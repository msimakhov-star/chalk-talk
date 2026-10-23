// Backend the TV talks to. Production Modal URL by default; the emulator can
// reach the internet directly, so no adb reverse is needed. For a local
// backend on the Mac, point this at http://10.0.2.2:8000 (emulator -> host).
export const BACKEND_URL = 'https://m-simakhov--chalk-talk-web.us-east.modal.run';

// What the Pair screen tells the coach to open on their phone.
export const PHONE_URL = BACKEND_URL + '/phone';

// The state endpoint long-polls for up to 10 s; abort a little after that.
export const POLL_TIMEOUT_MS = 15000;

// Wait before retrying after a network error.
export const RETRY_MS = 3000;

// How long a beat's caption stays on screen during auto-play before the next beat.
export const READ_PAUSE_MS = 1800;
