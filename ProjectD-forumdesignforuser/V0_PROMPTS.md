# v0.dev 프롬프트 가이드

MM.pro 커뮤니티 UI/UX 이미지 생성용

---

## 공통 스타일 (모든 프롬프트에 포함)

```
Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card surface: #F8FAFC, Secondary surface: #F1F5F9)
- Primary color: #6366F1 (Indigo)
- Bullish/Success: #22C55E (Green)
- Bearish/Danger: #EF4444 (Red)
- Text primary: #0F172A, Text secondary: #64748B
- Border/Divider: #E2E8F0
- Font: Pretendard (or Inter as fallback)
- Card-based layout with subtle shadows and light borders
- Rounded corners (8-12px)
- Korean text UI
- Toss-style clean and minimal aesthetic

⚠️ IMPORTANT: Generate BOTH versions for each screen:
1. Mobile version (375px width)
2. Desktop/PC version (1440px width, with sidebar)

Post card layout (when posts are shown):
- Thumbnail image on LEFT (square, 80-100px)
- Content on RIGHT: Title → Content preview → Author info
- Show BOTH variations:
  • With thumbnail: Image visible on left
  • Without thumbnail: No image, content expands to full width
```

---

## 게시글 카드 공통 레이아웃

```
Post Card Layout (applies to all feed screens):

WITH THUMBNAIL:
┌─────────────────────────────────────────┐
│ ┌──────┐  제목 (한 줄, 굵게)              │
│ │ 썸네일 │  본문 미리보기 (2줄까지)...      │
│ │ 이미지 │  👤 닉네임 · Lv.3 · 35분 전     │
│ └──────┘  ♡ 234 💬 56  🟢 강세           │
└─────────────────────────────────────────┘

WITHOUT THUMBNAIL:
┌─────────────────────────────────────────┐
│ 제목 (한 줄, 굵게)                        │
│ 본문 미리보기가 더 길게 표시됩니다 (3줄)... │
│ 👤 닉네임 · Lv.3 · 35분 전                │
│ ♡ 234 💬 56  🟢 강세                     │
└─────────────────────────────────────────┘

- Thumbnail: 1:1 ratio, rounded corners (8px)
- Title: Bold, single line with ellipsis
- Preview: 2-3 lines, secondary text color
- Meta row: Avatar, username, level, time
- Action row: Likes, comments, prediction tag
```

---

## 🔴 필수 이미지 (1~8)

---

### 1. 피드 - 최신글 탭

**v0.dev 프롬프트:**
```
Create a community feed screen for a Korean prediction market app called "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px with sidebar) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1, Bullish: #22C55E, Bearish: #EF4444
- Text primary: #0F172A, Text secondary: #64748B
- Border: #E2E8F0
- Korean text, Toss-style minimal design

Layout:
- Top: 3 tab buttons [최신글] [주제별 ▼] [뜨거운 반응], "최신글" is active
- Below tabs: Hot posts section with label "🔥 인기글" and small "전체보기" link
- 2 hot post cards (compact, horizontal layout)
- Main feed: vertical scrolling post cards

Post card layout (show BOTH with/without thumbnail):
WITH THUMBNAIL (left side, square 80px):
- [Thumbnail] | Title (bold, 1 line)
- [Image]     | Content preview (2 lines)...
-             | 👤 동글동글살자 · 🌳 Lv.3 · 35분 전
-             | ♡ 234 💬 56 · 🟢 강세 BTC $100k

WITHOUT THUMBNAIL:
- Title spans full width (bold)
- Content preview (3 lines)
- Meta info same as above

Desktop sidebar widgets:
- 인기 마켓 (trending markets)
- 이번 주 인기 예측러 (top predictors)

Show 2 hot posts + 3 regular feed posts. Include bottom navigation bar (mobile) / top navigation (desktop).
```

**문서 위치:** `## 1. 피드 구조` 섹션 상단

---

### 2. 피드 - 뜨거운 반응 탭

**v0.dev 프롬프트:**
```
Create a "Hot Posts" feed screen for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px with sidebar) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1, Bullish: #22C55E, Bearish: #EF4444
- Text primary: #0F172A, Text secondary: #64748B
- Korean text, clean Toss-style design

Layout:
- Top: 3 tabs [최신글] [주제별 ▼] [뜨거운 반응], "뜨거운 반응" is active (highlighted)
- No hot posts section at top (this IS the hot posts tab)
- Feed shows ranked hot posts with ranking numbers

Post card layout (show BOTH with/without thumbnail):
WITH THUMBNAIL:
- 🔥 1 rank badge | [Thumbnail] | Title + content preview
-                 |   80px     | 동글동글살자 · Lv.3 · 2시간 전
-                 |            | ♡ 1.2k 💬 342 · 🟢 강세 Trump 2024

WITHOUT THUMBNAIL:
- 🔥 1 rank badge on top left
- Full width title and content

Desktop sidebar: 인기 마켓, 이번 주 인기 예측러
Show posts ranked 1-4. Include engagement metrics prominently.
```

**문서 위치:** `## 1. 피드 구조` 섹션, "뜨거운 반응 탭" 설명 아래

---

### 3. 글 카드 비교 (일반/익명/종료)

**v0.dev 프롬프트:**
```
Create a comparison of 3 post card states for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Bullish: #22C55E, Bearish: #EF4444
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Show 3 post cards vertically with labels. Each card shows thumbnail layout:

Card 1 - "일반 글" (WITH THUMBNAIL):
- [Thumbnail 80px] | "비트코인 이번에 간다" (title, bold)
-                  | 본문 미리보기 텍스트...
-                  | 👤 동글동글살자 · 🌳 Lv.3 🎯 · 35분 전
-                  | ♡ 234 💬 56 · 🟢 강세 BTC $100k

Card 2 - "익명 글" (WITHOUT THUMBNAIL):
- "이번 선거 결과 어떻게 될까요?" (title spans full width)
- 본문 내용이 전체 너비로 표시됩니다...
- 🔵 졸린판다 (익명) · 10분 전
- ♡ 45 💬 12 · 🔴 약세 Trump 2024
- No level badge, subtle "(익명)" in gray

Card 3 - "마켓 종료된 글" (WITH THUMBNAIL):
- [Thumbnail] | "ETH 합병 성공할 듯" + "마켓 종료" badge
-             | 행복한고양이 · 🌿 Lv.2 · 3일 전
-             | ♡ 567 💬 89 · 🟢 강세 · 결과: ETH 합병 완료 ✓
- Result shown with checkmark, slightly muted color

Each card should be clearly labeled at the top.
```

**문서 위치:** `## 4. 익명 정책` 섹션 + `## 7. 마켓 종료 처리` 섹션

---

### 4. 글 상세 + 댓글

**v0.dev 프롬프트:**
```
Create a post detail screen with comments for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px with sidebar) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1, Bullish: #22C55E
- Text primary: #0F172A, Text secondary: #64748B
- Korean text, Toss-style

Layout:
- Top: Back arrow "←", "글 상세" title
- Post section:
  - Author: avatar, "동글동글살자 🌳 Lv.3 🎯 예측가", "35분 전", "..." menu
  - Content: "비트코인 이번에 10만 달러 확실히 간다고 봅니다. 기관들 매수세가 엄청나고..."
  - Post images (if any): Full width, 1-2 images shown
  - Market link card: "BTC $100k" with current price, small chart
  - Prediction tag: "🟢 강세"
  - Actions: "♡ 234", "💬 56", "🔖 북마크", "🚨 신고"

- Comments section:
  - "댓글 56개" header
  - Comment 1: "루키유저 🌿 Lv.2" - "동의합니다 ㅋㅋ" - "♡ 12" - "[답글]"
    - Reply (indented): "졸린판다 (익명)" - "저도요~" - "♡ 3"
  - Comment 2: "동글동글살자 🌳" (author badge) - "@루키유저 감사합니다" - "♡ 5"

- Bottom: Comment input field with send button
- Desktop: sidebar with related markets, author's other posts
```

**문서 위치:** `## 5. 댓글 시스템` 섹션

---

### 5. 글쓰기 (커뮤니티 탭)

**v0.dev 프롬프트:**
```
Create a post writing screen for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1, Bullish: #22C55E, Bearish: #EF4444
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top: "← 글쓰기" header with "게시" button (primary color)

- Category selection (prominent):
  - Label: "카테고리 선택"
  - "최근 사용" section with 3 pill buttons: [크립토] [정치] [선거]
  - "전체 보기 ▼" expandable link
  - Selected category highlighted with primary color border

- Title input:
  - Placeholder: "제목을 입력하세요 (2-100자)"

- Content area:
  - Large text area
  - Placeholder: "내용을 입력하세요 (최소 10자)"
  - Character count "0 / 10,000"

- Market connection (optional):
  - "마켓 연결" with search icon
  - When connected: shows market card preview

- Prediction selection:
  - "예측 방향" label
  - Two large buttons: [🟢 강세] [🔴 약세]

- Image upload:
  - "📷 이미지 추가 (0/20)"
  - Show image preview thumbnails when uploaded

- Desktop: Centered content area with max-width, preview panel on right
```

**문서 위치:** `## 2. 카테고리` 섹션

---

### 6. 유저 프로필

**v0.dev 프롬프트:**
```
Create a user profile screen for Korean prediction market community "MM.pro", inspired by Toss Securities profile.
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1
- Text primary: #0F172A, Text secondary: #64748B
- Korean text, Toss-style slide-in feel

Layout:
- Top: "← 커뮤니티" back button (indicates SPA navigation)

- Profile header:
  - Large avatar (80px)
  - Username: "동글동글살자"
  - Level: "🌳 Lv.3 레귤러"
  - Badges row: "🎯 예측가 실버", "✅ 인증"
  - Stats row: "글 34 · 팔로워 128 · 팔로잉 45"
  - Accuracy: "적중률 62% (50회)"
  - Bio: "비트코인 장기 투자자입니다"
  - [팔로우] button (primary color)

- Tab bar:
  - [전체 활동] [남긴 글] [예측 기록]
  - "전체 활동" selected

- Activity feed (show WITH/WITHOUT thumbnail posts):
  - Activity item 1 (with thumbnail): [Thumb] "비트코인에 글 작성 · 35분 전"
    - Preview: "10만 달러 간다"
    - "🟢 강세 · ♡ 23 💬 12"
  - Activity item 2 (no thumbnail): "ETH 합병 예측 · 2일 전"
    - "🟢 강세 예측 · 적중 ✅"

- Desktop: Two-column layout, activity on left, stats sidebar on right
```

**문서 위치:** `## 13. 프로필/계정` 섹션

---

### 7. 마켓 페이지 + 댓글 (메인)

**v0.dev 프롬프트:**
```
Create a market detail page with DC Inside-style comment section for Korean prediction market "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1, Bullish: #22C55E, Bearish: #EF4444
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top: Market header
  - "BTC $100k by Jan 2025"
  - Current odds: "Yes 67% / No 33%" with progress bar
  - Price chart (simple line)
  - Community sentiment: "🟢 강세 72% 🔴 약세 28%"

- Quick comment section (DC Inside style):
  - Simple input: "의견을 남겨주세요..." with send button
  - No login required indicator
  - "익명으로 작성됩니다" small text

- Comments feed:
  - "💬 실시간 의견 234개"
  - Comment: "졸린판다 (익명) · 5분 전" - "이번엔 진짜 갈 듯 ㅋㅋ" - "🟢 강세"
  - Comment: "행복한고양이 (익명) · 3분 전" - "에이 못 감 ㅋㅋ" - "🔴 약세"
  - Comments are casual, short, real-time feel

- Each comment shows prediction stance as colored tag
- Simple like count, no complex threading
- Desktop: Chart and market info on left, comments on right (split view)
```

**문서 위치:** `## 15. 서비스 구조` 섹션

---

### 8. 알림 목록

**v0.dev 프롬프트:**
```
Create a notifications screen for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top: "🔔 알림" header with "모두 읽음" text button, settings icon

- Notification list:

  Unread section (with blue dot indicator, light primary background):
  - "동글동글살자님 외 5명이 좋아요를 눌렀습니다" (grouped notification)
    - Stacked avatars (3 shown + "+3")
    - Preview: '"비트코인 이번에 간다" 글에'
    - "5분 전"

  - "졸린판다(익명)님이 댓글을 남겼습니다"
    - Preview: "ㅇㅈ 나도 그렇게 생각함"
    - "10분 전"

  - "🎯 BTC $100k 예측이 적중했습니다!"
    - Green success indicator
    - "1시간 전"

  Read section (normal background):
  - "내 글이 인기글에 올랐습니다 🔥"
    - "1일 전"

  - "예측가 실버 배지를 획득했습니다 🎉"
    - "2일 전"

- Each notification is tappable with subtle hover state
- Desktop: Centered content with max-width 600px
```

**문서 위치:** `## 8. 알림 시스템` 섹션

---

## 🟡 권장 이미지 (9~13)

---

### 9. 주제별 탭 + 카테고리 드롭다운

**v0.dev 프롬프트:**
```
Create a feed screen showing category dropdown for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top tabs: [최신글] [주제별: 크립토 ▼] [뜨거운 반응]
- "주제별" tab is active and shows dropdown

- Dropdown overlay (bottom sheet on mobile, dropdown on desktop):
  - Header: "카테고리 선택"
  - Grid of category pills (2-3 columns):
    - 정치, 선거, 크립토 ✓ (selected), 스포츠
    - 금융, 경제, 기술, 문화
    - 지정학, 세계, 기후/과학, 기업실적
    - 기타
  - Selected category has checkmark and primary color border

- Behind dropdown (dimmed):
  - Hot posts section for selected category
  - "🔥 크립토 인기글"
  - Feed posts with thumbnail layout (some with, some without images)
```

**문서 위치:** `## 2. 카테고리` 섹션

---

### 10. 검색 결과 + 필터

**v0.dev 프롬프트:**
```
Create a search results screen with filters for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top: Search bar with "비트코인" query, X clear button
- Filter chips row (horizontally scrollable):
  - [전체 ▼] [기간: 1주 ▼] [레벨: 전체 ▼] [예측: 전체 ▼]
  - Active filter has primary color background

- Results tabs: [글 24] [유저 3] - "글" selected

- Search results (post cards with thumbnail layout):
  - Result 1: [Thumb] | Title with highlighted "비트코인" keyword
  - Result 2: No thumbnail, full width layout
  - Result 3: With thumbnail

- Sort option: "최신순 ▼" (default)

- Desktop: Filters in sidebar, results in main area
```

**문서 위치:** `## 9. 검색/북마크` 섹션

---

### 11. 북마크 목록

**v0.dev 프롬프트:**
```
Create a bookmarks screen for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top: "📑 북마크" header with count "총 23개"

- Bookmark list (simple, no folders):

  - Bookmark 1 (Post with thumbnail):
    - [Thumbnail] | "비트코인 이번에 간다"
    -             | "동글동글살자 · 2일 전 저장"

  - Bookmark 2 (Comment, no thumbnail):
    - "💬" icon
    - "ㅇㅈ 이건 진짜 맞는 말"
    - "졸린판다(익명) 댓글 · 3일 전 저장"

  - Bookmark 3 (User):
    - Avatar + "동글동글살자"
    - "유저 · 1주 전 저장"

  - Bookmark 4 (Deleted post):
    - Grayed out style
    - "[삭제된 글입니다]"
    - "5일 전 저장"

- Each item has swipe-to-delete (mobile) or "..." menu (desktop)
- Desktop: Grid layout for posts, list for comments/users
```

**문서 위치:** `## 9. 검색/북마크` 섹션

---

### 12. 신고 팝업

**v0.dev 프롬프트:**
```
Create a report popup/bottom sheet for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px bottom sheet) and desktop (1440px centered modal) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Danger: #EF4444
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Bottom sheet (mobile) / Centered modal (desktop) with dimmed overlay

- Sheet content:
  - Header: "🚨 신고하기" with X close button
  - Subtext: "이 글을 신고하는 이유를 선택해주세요 (복수 선택 가능)"

  - Checkbox list:
    - ☑️ 스팸/광고 (checked example)
    - ☐ 욕설/비하
    - ☑️ 허위 정보 (checked example)
    - ☐ 도배
    - ☐ 기타

  - "기타" text input (appears when 기타 selected):
    - Placeholder: "신고 사유를 직접 입력해주세요"

  - Warning text: "허위 신고 시 제재를 받을 수 있습니다"

  - Submit button: "신고하기" (red/danger color)

- Shows multiple selection state
```

**문서 위치:** `## 10. 신고/차단` 섹션

---

### 13. 프로필 설정

**v0.dev 프롬프트:**
```
Create a profile settings screen for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top: "← 프로필 설정" header with "저장" button

- Profile image section:
  - Large avatar with camera overlay icon
  - "사진 변경" button

- Form fields:

  - 닉네임:
    - Input: "동글동글살자"
    - Helper: "2-15자, 90일마다 변경 가능"
    - Status: "다음 변경 가능: 45일 후"

  - 자기소개:
    - Textarea: "비트코인 장기 투자자입니다"
    - Character count: "23 / 100"

- Section divider

- Settings list:
  - "알림 설정" with toggle (ON)
  - "차단 목록 관리" with arrow
  - "계정 탈퇴" in red text with arrow

- Desktop: Centered card layout with max-width 600px
```

**문서 위치:** `## 13. 프로필/계정` 섹션

---

## 🟢 있으면 좋음 이미지 (14~17)

---

### 14. Privy 로그인

**v0.dev 프롬프트:**
```
Create a login screen using Privy auth for Korean prediction market "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Primary: #6366F1
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Center: MM.pro logo (placeholder)
- Tagline: "예측하고, 토론하고, 증명하세요"

- Login options (Privy style):
  - Large button: "🔗 지갑으로 시작하기" (primary)
    - Subtext: "MetaMask, WalletConnect 등"

  - Divider: "또는"

  - Button: "Continue with Google" (with Google icon, outlined)
  - Button: "Continue with Apple" (with Apple icon, outlined)
  - Button: "이메일로 시작하기"

- Bottom text:
  - "계속 진행하면 이용약관 및 개인정보처리방침에 동의하게 됩니다"

- Clean, centered layout
- Trust indicators: "Powered by Privy" small text
- Desktop: Centered card with max-width 400px, subtle shadow
```

**문서 위치:** `## 13. 프로필/계정` 섹션, "회원가입" 부분

---

### 15. 차단 목록

**v0.dev 프롬프트:**
```
Create a blocked users list screen for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top: "← 차단 목록" header

- Info card (light blue/gray background):
  - "차단된 사용자의 글과 댓글은 보이지 않습니다"

- Blocked users list:

  - User 1:
    - Avatar, "스팸유저123"
    - "차단일: 2025.01.15"
    - [차단 해제] button (outlined)

  - User 2:
    - Avatar, "트롤러456"
    - "차단일: 2025.01.10"
    - [차단 해제] button

  - User 3:
    - Avatar (grayed), "탈퇴한 사용자"
    - "차단일: 2024.12.20"
    - [차단 해제] button (disabled state)

- Empty state (if no blocked users):
  - "차단한 사용자가 없습니다"

- Desktop: Centered list with max-width 600px
```

**문서 위치:** `## 10. 신고/차단` 섹션

---

### 16. 수정/삭제 확인 팝업

**v0.dev 프롬프트:**
```
Create confirmation popups for edit/delete actions in Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Danger: #EF4444
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Show 2 popup states:

Popup 1 - "글 삭제 확인":
- Center modal with dimmed background
- Icon: Warning/trash icon (red)
- Title: "글을 삭제하시겠습니까?"
- Message: "댓글 12개가 함께 삭제됩니다.\n삭제된 글은 복구할 수 없습니다."
- Buttons: [취소] (ghost) [삭제] (red/danger)

Popup 2 - "수정 불가 안내":
- Center modal
- Icon: Info icon (gray)
- Title: "수정할 수 없습니다"
- Message: "글 작성 후 10분이 지나 수정할 수 없습니다."
- Timer indicator: "수정 가능 시간이 만료되었습니다"
- Button: [확인] (primary)

- Modal width: 320px (mobile), 400px (desktop)
```

**문서 위치:** `## 6. 글 수정/삭제` 섹션

---

### 17. 탈퇴 확인

**v0.dev 프롬프트:**
```
Create an account withdrawal confirmation screen for Korean prediction market community "MM.pro".
Generate BOTH mobile (375px) and desktop (1440px) versions.

Style guide:
- WHITE/LIGHT mode UI (Background: #FFFFFF, Card: #F8FAFC)
- Danger: #EF4444
- Text primary: #0F172A, Text secondary: #64748B
- Korean text

Layout:
- Top: "← 계정 탈퇴" header

- Warning section:
  - Large warning icon (red)
  - Title: "정말 탈퇴하시겠습니까?"

- Info list (card with light red/pink background):
  - "✓ 탈퇴 후 7일간 철회 가능합니다"
  - "✓ 작성한 글과 댓글은 유지됩니다"
  - "✓ 닉네임은 '탈퇴한 사용자'로 변경됩니다"
  - "✓ 예측 기록은 익명화되어 통계용으로 보관됩니다"
  - "✓ 탈퇴 후 30일간 재가입할 수 없습니다"

- Confirmation:
  - Checkbox: "위 내용을 모두 확인했습니다"

- Buttons:
  - [취소] (ghost, full width)
  - [탈퇴하기] (red/danger, full width, disabled until checkbox)

- Desktop: Centered card layout with max-width 500px
```

**문서 위치:** `## 13. 프로필/계정` 섹션, "탈퇴" 부분

---

## 사용 팁

1. **프롬프트 복사 시** 공통 스타일 가이드 + 게시글 카드 레이아웃도 함께 포함
2. **두 버전 요청** 각 프롬프트에 "Generate BOTH mobile and desktop versions" 명시됨
3. **한 번에 1개씩** 생성 후 수정하며 크레딧 절약
4. **결과가 다르면** 다음 추가 지시 사용:
   - "Make it lighter/cleaner" - 더 밝고 깔끔하게
   - "Add more whitespace" - 여백 추가
   - "Show post cards with and without thumbnails" - 썸네일 유무 버전 모두
5. **한국어 텍스트**가 깨지면 "Use Korean text: [원하는 텍스트]" 명시

## 체크리스트

각 이미지 생성 시 확인:
- [ ] 화이트/라이트 모드인가?
- [ ] 모바일(375px) + 데스크탑(1440px) 두 버전인가?
- [ ] 게시글 카드에 썸네일 있는/없는 버전이 모두 있는가?
- [ ] 데스크탑에 사이드바(인기 마켓, 인기 예측러)가 있는가?

---

*작성: 2025-02-03*
*수정: 2025-02-03 (화이트모드, 듀얼버전, 썸네일 레이아웃 추가)*
