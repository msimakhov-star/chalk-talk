# Demo video: storyboard and voiceover (target 2:45, hard cap 3:00)

Rules the video must obey: under 3 minutes, public on YouTube, English, no third-party trademarks, music or footage. Everything on screen is our own UI. The emulator is labelled "Android TV emulator (Fire OS stand-in)". Say the track tools out loud: "React Native for TV", "MCP server", "MCP Apps".

Voiceover at about 150 words per minute; each beat lists the words and the screen.

## Beat 1, 0:00 to 0:20, the problem (whiteboard)

Screen: our own whiteboard mock, X's and O's and arrows, then a blank-faced kid emoji is NOT used; instead the text "Ten-year-olds don't read diagrams" fades in.

Voice: "Every volunteer youth coach has drawn this. Five circles, five crosses, a few arrows. And every ten-year-old has looked at it and seen nothing. Kids don't read diagrams. They watch. Chalk Talk turns a play you say or sketch on your phone into a play the whole team can watch on the TV."

## Beat 2, 0:20 to 0:55, sketch on the phone, play on the TV

Screen: phone page (390 px frame) on the left, Android TV emulator on the right. Coach draws two strokes on the court; taps "Draw the play". The TV animates "Pick and roll, right wing". D-pad right steps beat by beat; the caption shows the title and the read.

Voice: "The coach sketches on the phone. Chalk Talk recognises the shape, picks the matching play from its library of eight templates, and the TV animates it. Each step has one line a kid can follow: 'wait for the screen, then go shoulder to shoulder'. The remote's D-pad steps forward and back. This is a React Native app for TV, running here on the Android TV emulator as a stand-in for Fire OS."

## Beat 3, 0:55 to 1:25, say it, then "what if they switch?"

Screen: phone "Say it" button, transcript "backdoor cut from the left wing". TV shows the new play. Then "what if they switch?" and the defence re-plans; badge changes to "vs switch"; the read changes.

Voice: "Or just say it. 'Backdoor cut from the left wing.' A language model maps the words to a template and its parameters; it never draws freehand, so every play passes a validator: nobody out of bounds, nobody running through a teammate, nobody faster than a real kid. Now the coaching moment: 'what if they switch?' The defence re-plans live, and the read tells the kids what to look for against a switch."

## Beat 4, 1:25 to 1:55, the kitchen screen (Alexa+ via MCP)

Screen: the Echo Show simulator in the browser (labelled "Smart display simulator speaking MCP"). Transcript: "what are we practising on Thursday?" A practice plan card appears. Then "show me the playbook" (carousel). Then "send the pick and roll to the TV": confirmation card; the TV on the right updates.

Voice: "Chalk Talk is also an Alexa+ style add-on: a self-hosted MCP server with six tools and MCP Apps views, which we demo on a smart-display simulator that speaks real MCP over streamable HTTP. 'What are we practising on Thursday?' builds a practice plan from the saved playbook. 'Send the pick and roll to the TV' hands the play to the living room. The simulator is open source, so any developer can demo their own MCP server the same way."

## Beat 5, 1:55 to 2:30, how it works and the numbers

Screen: one architecture slide (phone / TV / smart display -> backend on Modal -> template engine + validator + small open model). Then the evaluation table: freehand model coordinates vs template engine, columns out-of-bounds, overlaps, too fast, valid plays; and phone-to-TV latency p50/p95.

Voice: "Under the hood: one backend serves the TV, the phone and the MCP server. We measured why templates matter. Asked to place players freehand, the model produced invalid plays {VERIFY}% of the time. Through the template engine, zero. And from tap on the phone to motion on the TV takes about {VERIFY} seconds."

## Beat 6, 2:30 to 2:50, status and how to try it

Screen: honest status table (built, tested on emulator, simulated, not done). Then the repo URL, the simulator URL and "APK in the repo".

Voice: "Here is exactly what is built and what is not. Try the smart-display simulator in your browser right now, sideload the APK on a Fire TV, and read the friction log: the things we hit so the next developer doesn't. Chalk Talk. Say the play. Watch it happen."

## Production notes

- Record the phone page with playwright-cli video at 390x844 and the emulator window with the macOS screen recorder (or adb screenrecord, limited to 3 minutes per file) at the same time, then composite side by side with ffmpeg.
- Voiceover: a single narrator voice, consistent across beats; generate per beat so timing can be adjusted.
- Caption burn-in for the key phrases (play names, "vs switch").
- Export 1920x1080, H.264, AAC, under 300 MB.
