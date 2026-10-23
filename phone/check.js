// Phone page self-check. Drives phone/index.html and renderer/demo.html in headless
// Chromium at 390x844, asserts the flows work, and writes phone/screenshots/*.png.
//
//   cd <repo root>
//   python3 -m http.server 8765 --bind 127.0.0.1 &
//   playwright-cli run-code --filename=phone/check.js
//
// playwright-cli's run-code sandbox has no process/require/URL, so the two
// constants below are plain strings. Edit OUT to your checkout path.
async page => {
  const BASE = 'http://127.0.0.1:8765';
  const OUT = process.cwd() + '/phone/screenshots/';  // run from the repo root

  const assert = (ok, what) => { if (!ok) throw new Error('CHECK FAILED: ' + what); };
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  const toastText = () => page.textContent('#toast');

  await page.setViewportSize({ width: 390, height: 844 });

  // ---- A. mock mode (?mock=1): no backend, answers come from the renderer fixture ----
  await page.goto(BASE + '/phone/index.html?mock=1');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.screenshot({ path: OUT + '01-empty.png' });

  // Draw one stroke from the right wing to the rim; strokes must land in court feet.
  const box = await page.locator('#sketch').boundingBox();
  const px = (x, y) => [box.x + (x / 50) * box.width, box.y + (1 - y / 47) * box.height];
  const waypoints = [[42, 28], [40, 24], [37, 18], [33, 12], [28, 7.5], [26, 6]];
  await page.mouse.move(...px(...waypoints[0]));
  await page.mouse.down();
  for (const p of waypoints.slice(1)) await page.mouse.move(...px(...p), { steps: 4 });
  await page.mouse.up();
  const strokes = await page.evaluate(() => window.chalkPhone.strokes);
  assert(strokes.length === 1 && strokes[0].length >= 6, 'one stroke with several points recorded');
  const [sx, sy] = strokes[0][0];
  const [ex, ey] = strokes[0][strokes[0].length - 1];
  assert(Math.abs(sx - 42) < 1 && Math.abs(sy - 28) < 1, `stroke starts near (42,28), got (${sx},${sy})`);
  assert(Math.abs(ex - 26) < 1 && Math.abs(ey - 6) < 1, `stroke ends near (26,6), got (${ex},${ey})`);

  await page.fill('#text', 'pick and roll on the right');
  await page.screenshot({ path: OUT + '02-sketch-and-text.png' });

  await page.click('#draw');
  await page.waitForFunction(() => window.chalkPhone.play);
  const understood = await page.textContent('#understood');
  assert(understood === 'understood as: Pick and roll, right wing (rules, 0.9)', 'understood line: ' + understood);
  assert((await page.evaluate(() => getComputedStyle(document.getElementById('defenceBadge')).display)) === 'none', 'no badge for man defence');
  await page.waitForTimeout(1000);
  const tAfter = await page.evaluate(() => window.chalkPhone.t);
  assert(tAfter > 0.5 && tAfter < 3, 'preview animates in real time, t=' + tAfter);
  await page.evaluate(() => window.chalkPhone.jumpToBeat(2));
  await page.locator('#result').scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  assert((await page.textContent('#beatTitle')).startsWith('Use the screen'), 'caption follows the beat');
  await page.screenshot({ path: OUT + '03-result.png' });

  await page.click('#counters button[data-defence=switch]');
  await page.waitForFunction(() => window.chalkPhone.play.defence === 'switch');
  assert((await page.textContent('#defenceBadge')) === 'vs switch', 'badge shows the counter');
  assert((await page.textContent('#playName')) === 'Pick and roll, right wing vs switch', 'counter name');
  await page.evaluate(() => window.chalkPhone.jumpToBeat(1));
  await page.waitForTimeout(200);
  await page.screenshot({ path: OUT + '04-counter-switch.png' });

  await page.click('#send');
  await page.waitForTimeout(150);
  assert((await toastText()).includes('TV code first'), 'send without a code is refused');
  await page.fill('#code', 'kqzt');
  assert((await page.textContent('#codeStatus')).includes('KQZT'), 'code is upper-cased and acknowledged');
  await page.click('#send');
  await page.waitForFunction(() => document.getElementById('toast').textContent.includes('Showing'));
  await page.screenshot({ path: OUT + '05-sent-to-tv.png' });
  assert((await page.evaluate(() => localStorage.getItem('chalk.tvCode'))) === 'KQZT', 'code saved in localStorage');
  await page.screenshot({ path: OUT + '00-full-page.png', fullPage: true });

  // ---- B. real fetch path with ?api= override; the backend is stubbed with page.route ----
  const requests = [];
  const fixture = await (await page.request.get(BASE + '/renderer/fixtures/pick_and_roll.json')).json();
  await page.route('http://localhost:8000/**', async (route) => {
    const req = route.request();
    const path = req.url().replace(/^https?:\/\/[^/]+/, '').split('?')[0];
    requests.push({ method: req.method(), path, body: req.postDataJSON() });
    if (path === '/api/tv/ZZZZ/command') {
      return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { code: 'unknown_tv', message: 'No TV with that code' } }) });
    }
    let body = { ok: true, cursor: 7 };
    if (path === '/api/plays') body = fixture;
    if (path.endsWith('/counter')) body = { ...fixture, id: fixture.id + '-hedge', defence: 'hedge', name: fixture.name + ' vs hedge' };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.goto(BASE + '/phone/index.html?api=http://localhost:8000');
  assert((await page.evaluate(() => window.chalkPhone.API)) === 'http://localhost:8000', '?api= override');
  assert((await page.inputValue('#code')) === 'KQZT', 'code restored from localStorage');
  await page.click('#ppsSegment button[data-value="3"]');
  await page.selectOption('#age', 'u10');
  await page.fill('#text', 'backdoor cut from the left wing');
  await page.click('#draw');
  await page.waitForFunction(() => window.chalkPhone.play);
  await page.click('#counters button[data-defence=hedge]');
  await page.waitForFunction(() => document.getElementById('toast').textContent.includes('Showing'));
  await page.fill('#code', 'ZZZZ');
  await page.click('#send');
  await page.waitForFunction(() => document.getElementById('toast').textContent.includes('failed'));
  assert((await toastText()) === 'Send failed: No TV with that code', 'backend error envelope reaches the toast');

  const [plays, counter, command] = requests;
  assert(plays.method === 'POST' && plays.path === '/api/plays', 'POST /api/plays');
  assert(plays.body.text === 'backdoor cut from the left wing' && plays.body.players_per_side === 3 && plays.body.age_group === 'u10' && !('sketch' in plays.body), 'play body: ' + JSON.stringify(plays.body));
  assert(counter.path === '/api/plays/ply_a1b2c3/counter' && counter.body.defence === 'hedge', 'counter request');
  assert(command.path === '/api/tv/KQZT/command' && command.body.type === 'show_play' && command.body.play_id === 'ply_a1b2c3-hedge', 'show_play command: ' + JSON.stringify(command));

  // ---- C. renderer demo: plays, steps, scrubs ----
  await page.setViewportSize({ width: 900, height: 1000 });
  await page.goto(BASE + '/renderer/demo.html');
  await page.waitForFunction(() => window.chalkDemo);
  await page.click('#toggle');
  await page.waitForTimeout(800);
  const demoT = await page.evaluate(() => window.chalkDemo.t);
  assert(demoT > 0.4 && demoT < 3, 'demo plays, t=' + demoT);
  await page.click('#toggle');
  await page.evaluate(() => window.chalkDemo.jumpToBeat(3));
  assert((await page.textContent('#title')).startsWith('Roll'), 'demo step to beat 4');
  await page.evaluate(() => { const s = document.getElementById('scrub'); s.value = 7; s.dispatchEvent(new Event('input')); });
  assert((await page.textContent('#time')) === '7.0 s', 'demo scrubber');
  await page.screenshot({ path: OUT + '06-renderer-demo.png' });

  const realErrors = errors.filter((e) => !e.includes('404'));
  assert(realErrors.length === 0, 'console/page errors: ' + realErrors.join(' | '));
  return { ok: true, strokePoints: strokes[0].length, understood, requests: requests.length, ignored404s: errors.length };
}
