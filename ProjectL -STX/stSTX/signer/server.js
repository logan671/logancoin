"use strict";

const http = require("http");
const {
  uintCV,
  tupleCV,
  contractPrincipalCV,
  cvToHex,
  deserializeCV,
  cvToValue,
  makeContractCall,
  broadcastTransaction,
  AnchorMode,
  PostConditionMode,
} = require("@stacks/transactions");
const { StacksMainnet } = require("@stacks/network");

const PORT = Number(process.env.SIGNER_PORT || "8788");
const AUTH_TOKEN = String(process.env.SIGNER_API_TOKEN || "").trim();
const HIRO_API_BASE = String(process.env.SIGNER_HIRO_API_BASE || "https://api.hiro.so").replace(/\/+$/, "");

const SWAP = {
  addr: "SM1793C4R5PZ4NS4VQ4WMP7SKKYVH8JZEWSZ9HCCR",
  helper: "stableswap-swap-helper-v-1-4",
  helperFn: "swap-helper-a",
  quoteFn: "get-quote-a",
  poolAddr: "SM1793C4R5PZ4NS4VQ4WMP7SKKYVH8JZEWSZ9HCCR",
  poolName: "stableswap-pool-stx-ststx-v-1-4",
  stxTokenAddr: "SM1793C4R5PZ4NS4VQ4WMP7SKKYVH8JZEWSZ9HCCR",
  stxTokenName: "token-stx-v-1-2",
  ststxTokenAddr: "SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG",
  ststxTokenName: "ststx-token",
  senderForRead: "SP000000000000000000002Q6VF78",
};

function json(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", chunk => chunks.push(chunk));
    req.on("end", () => {
      try {
        const raw = Buffer.concat(chunks).toString("utf-8").trim();
        resolve(raw ? JSON.parse(raw) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

function requireAuth(req) {
  if (!AUTH_TOKEN) return true;
  const auth = String(req.headers.authorization || "");
  return auth === `Bearer ${AUTH_TOKEN}`;
}

function principalTupleForAction(action) {
  if (action === "BUY_STSTX") {
    return {
      a: contractPrincipalCV(SWAP.stxTokenAddr, SWAP.stxTokenName),
      b: contractPrincipalCV(SWAP.ststxTokenAddr, SWAP.ststxTokenName),
    };
  }
  if (action === "SELL_STSTX") {
    return {
      a: contractPrincipalCV(SWAP.ststxTokenAddr, SWAP.ststxTokenName),
      b: contractPrincipalCV(SWAP.stxTokenAddr, SWAP.stxTokenName),
    };
  }
  throw new Error("unsupported_action");
}

async function fetchJson(url, opts = {}) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`http_${r.status}:${text.slice(0, 200)}`);
  }
  return r.json();
}

async function fetchPrices() {
  const url =
    "https://api.coingecko.com/api/v3/simple/price?ids=blockstack,stacking-dao&vs_currencies=usd";
  const j = await fetchJson(url);
  const stxUsd = Number(j?.blockstack?.usd || 0);
  const ststxUsd = Number(j?.["stacking-dao"]?.usd || 0);
  if (!(stxUsd > 0) || !(ststxUsd > 0)) {
    throw new Error("invalid_price_feed");
  }
  return { stxUsd, ststxUsd };
}

function pricesFromPayload(payload) {
  const stxUsd = Number(payload?.stx_usd || 0);
  const ststxUsd = Number(payload?.ststx_usd || 0);
  if (!(stxUsd > 0) || !(ststxUsd > 0)) {
    return null;
  }
  return { stxUsd, ststxUsd };
}

function amountMicroFromUsd(orderUsd, action, prices) {
  const usd = action === "BUY_STSTX" ? prices.stxUsd : prices.ststxUsd;
  const units = orderUsd / usd;
  const micro = Math.floor(units * 1_000_000);
  return BigInt(Math.max(1, micro));
}

async function fetchQuoteOut(amountMicro, tokenTupleCv) {
  const args = [
    cvToHex(uintCV(amountMicro)),
    cvToHex(tokenTupleCv),
    cvToHex(tupleCV({ a: contractPrincipalCV(SWAP.poolAddr, SWAP.poolName) })),
  ];
  const url = `${HIRO_API_BASE}/v2/contracts/call-read/${SWAP.addr}/${SWAP.helper}/${SWAP.quoteFn}`;
  const body = { sender: SWAP.senderForRead, arguments: args };
  const j = await fetchJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!j.okay) {
    throw new Error(`quote_failed:${j.cause || "unknown"}`);
  }
  const clarity = cvToValue(deserializeCV(j.result));
  const v = BigInt(String(clarity.value));
  if (v <= 0n) {
    throw new Error("quote_non_positive");
  }
  return v;
}

function minReceivedFromQuote(quoteOut, slippagePct) {
  const extra = 0.2;
  const pct = Math.max(0.5, Number(slippagePct || 0) + extra);
  const keepRatio = Math.max(0, 1 - pct / 100);
  const minOut = BigInt(Math.max(1, Math.floor(Number(quoteOut) * keepRatio)));
  return minOut;
}

function normalizePrivKey(raw) {
  let key = String(raw || "").trim();
  if (key.startsWith("0x")) key = key.slice(2);
  return key;
}

async function signAndBroadcast(payload) {
  const signerPk = normalizePrivKey(process.env.SIGNER_PRIVATE_KEY || "");
  if (!signerPk) {
    throw new Error("missing_signer_private_key");
  }

  const action = String(payload.action || "");
  const orderUsd = Number(payload.order_usd || 0);
  if (!(orderUsd > 0)) {
    throw new Error("invalid_order_usd");
  }

  const feeStx = Number(payload.fee_stx || 0);
  const feeMicro = BigInt(Math.max(1, Math.floor(feeStx * 1_000_000)));

  const prices = pricesFromPayload(payload) || (await fetchPrices());
  const amountMicro = amountMicroFromUsd(orderUsd, action, prices);
  const tokenTuple = tupleCV(principalTupleForAction(action));
  const quoteOut = await fetchQuoteOut(amountMicro, tokenTuple);
  const minOut = minReceivedFromQuote(quoteOut, Number(payload.slippage_pct || 0));

  const network = new StacksMainnet({ url: HIRO_API_BASE });
  const txOptions = {
    network,
    senderKey: signerPk,
    contractAddress: SWAP.addr,
    contractName: SWAP.helper,
    functionName: SWAP.helperFn,
    functionArgs: [
      uintCV(amountMicro),
      uintCV(minOut),
      tokenTuple,
      tupleCV({ a: contractPrincipalCV(SWAP.poolAddr, SWAP.poolName) }),
    ],
    fee: feeMicro,
    postConditionMode: PostConditionMode.Allow,
    anchorMode: AnchorMode.Any,
    validateWithAbi: false,
  };
  const tx = await makeContractCall(txOptions);
  const br = await broadcastTransaction(tx, network);
  if (typeof br === "string") {
    return { txid: br, status: "submitted", reason: "broadcasted" };
  }
  if (br && typeof br === "object") {
    if (br.error) {
      throw new Error(`broadcast_failed:${String(br.error)}:${String(br.reason || br.message || "")}`);
    }
    if (br.txid) {
      return { txid: String(br.txid), status: "submitted", reason: "broadcasted" };
    }
  }
  throw new Error("broadcast_failed:unknown:");
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/health") {
      return json(res, 200, { ok: true, service: "stx-ststx-signer" });
    }

    if (req.method === "POST" && req.url === "/sign-and-broadcast") {
      if (!requireAuth(req)) {
        return json(res, 401, { ok: false, status: "failed", reason: "unauthorized" });
      }

      const body = await parseBody(req);
      const result = await signAndBroadcast(body);
      return json(res, 200, {
        ok: true,
        status: result.status,
        reason: result.reason,
        txid: result.txid,
        fee_stx: Number(body.fee_stx || 0),
      });
    }

    return json(res, 404, { ok: false, status: "failed", reason: "not_found" });
  } catch (err) {
    return json(res, 500, {
      ok: false,
      status: "failed",
      reason: String(err && err.message ? err.message : err),
    });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`stx-ststx-signer listening on 127.0.0.1:${PORT}`);
});
