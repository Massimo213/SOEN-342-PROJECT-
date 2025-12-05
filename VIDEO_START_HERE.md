# START HERE - 5-MINUTE VIDEO GUIDE

## WHAT YOU NEED TO DO

You need to record a **5-minute video** demonstrating your complete SOEN 342 project from Iteration 1 through Final Iteration.

---

## STEP 1: PRACTICE FIRST (Do this NOW)

Run the practice script to:
1. Ensure all commands work
2. Get timing feedback
3. See what the output looks like

```bash
cd /Users/yahyamounadi/Desktop/Soen-342
./practice_demo.sh
```

This will:
- Run through all demo commands
- Show you exactly what will display
- Tell you if you're too fast/slow
- Take ~4-5 minutes

**Run this 2-3 times until you're comfortable.**

---

## STEP 2: READ THE FULL SCRIPT

Open and read: **`VIDEO_DEMO_SCRIPT.md`**

This contains:
- Complete timing breakdown (what to say at each timestamp)
- All commands with explanations
- What to emphasize
- Tips for recording
- Alternative fast-paced version if needed

---

## STEP 3: PREPARE YOUR RECORDING SETUP

### Terminal Setup:
```bash
cd /Users/yahyamounadi/Desktop/Soen-342
clear
# Press Cmd + Plus to increase font size (2-3 times)
```

### Open These in Separate Windows:
1. **Terminal** (main window) - for running commands
2. **VS Code** - open this project folder
3. **Browser** - navigate to your GitHub repo

### Screen Recording Software:
- **macOS:** QuickTime Player (File → New Screen Recording)
- **Alternative:** OBS Studio (free, more features)

---

## STEP 4: WHAT TO SHOW IN ORDER

### [0:00-0:30] Introduction (30 sec)
- **Show:** Terminal with project directory
- **Say:** "This is the Rail Network Booking System for SOEN 342..."
- **Run:** Basic commands (ls, stats)

### [0:30-1:15] Iteration 1 (45 sec)
- **Show:** Search commands working
- **Say:** "Direct and multi-stop search functionality..."
- **Run:** 2 search commands (direct, 1-stop)

### [1:15-2:00] Iteration 2 (45 sec)
- **Show:** Booking functionality
- **Say:** "Trip booking with unique ticket IDs..."
- **Run:** Booking command, show trip ID and tickets

### [2:00-3:00] Iteration 3 (60 sec)
- **Show:** Database, layover validation, numeric IDs
- **Say:** "Database persistence and smart layover policy..."
- **Run:** 3 commands (DB load, layover validation, DB booking)

### [3:00-4:00] Final Iteration (60 sec)
- **Show:** OCL constraints, state machine
- **Say:** "Formal specifications and state machine implementation..."
- **Run:** OCL enforcement demo, state machine flow
- **Quick flip:** Show state machine diagram in VS Code

### [4:00-5:00] Documentation & Tests (60 sec)
- **Show:** docs/ and diagrams/ folders
- **Say:** "Professional documentation and comprehensive testing..."
- **Run:** Test commands (both test files)
- **Show:** Git log and tags
- **End:** Final summary screen

---

## STEP 5: RECORDING CHECKLIST

### Before You Hit Record:
- [ ] Clear terminal: `clear`
- [ ] Font size increased: `Cmd + Plus` (2-3 times)
- [ ] In correct directory: `/Users/yahyamounadi/Desktop/Soen-342`
- [ ] Close unnecessary apps/notifications
- [ ] Test microphone audio level
- [ ] Have `QUICK_DEMO_COMMANDS.md` open on second screen

### While Recording:
- [ ] Speak clearly and confidently (not too fast!)
- [ ] Pause briefly after command output (let viewer read)
- [ ] Don't panic if something takes a second to run
- [ ] If you mess up badly, just stop and restart

### After Recording:
- [ ] Watch it back (check audio, readability)
- [ ] Verify it's 4-6 minutes (5 minutes target)
- [ ] Check that key points are clear:
  - "Complete software system, not just code"
  - "Six UML diagrams"
  - "Formal OCL specifications"
  - "44 tests, all passing"

---

## STEP 6: USE THE CHEAT SHEET DURING RECORDING

Keep **`QUICK_DEMO_COMMANDS.md`** open on a second screen.

This has:
- All commands in order
- What to say at each step
- No extra explanations (just the essentials)

---

## QUICK REFERENCE: KEY COMMANDS

### Iteration 1:
```bash
python3 app.py --csv eu_rail_network.csv --from Amsterdam --to Brussels --max-stops 0 --format table --limit 2
```

### Iteration 2:
```bash
python3 -c "from rail_network import RailNetwork; from booking_system import BookingSystem; ..."
```

### Iteration 3:
```bash
python3 -c "from database import Database; db = Database(':memory:'); ..."
```

### Final:
```bash
head -40 docs/ocl-constraints.md
python3 test_iteration3.py
python3 test_final_iteration.py
```

---

## WHAT YOUR TA WANTS TO SEE

1. **Progression through iterations** - Show how system evolved
2. **Working code** - Commands execute successfully
3. **Software engineering artifacts** - Not just code
4. **Documentation** - UML, requirements, architecture
5. **Testing** - Comprehensive test coverage
6. **Professional quality** - This is production-ready work

---

## IF YOU GET STUCK

### Commands Failing?
- Run `./practice_demo.sh` again to debug
- Check you're in the right directory
- Ensure virtual environment is activated if needed

### Running Over 5 Minutes?
- Use commands from `QUICK_DEMO_COMMANDS.md` (condensed version)
- Skip some intermediate outputs
- Speak slightly faster

### Running Under 5 Minutes?
- Good! Add more explanation as you go
- Show one more UML diagram in VS Code
- Pause longer after command outputs

---

## FINAL TIPS

### What Makes a Strong Demo:

**DO:**
- Speak confidently (you built something solid)
- Show progression through iterations
- Emphasize "complete software system"
- Mention UML diagrams, OCL, tests
- Show tests passing
- End with strong summary

**DON'T:**
- Rush through commands
- Apologize or sound uncertain
- Skip showing documentation
- Forget to mention testing
- Go over 6 minutes

### Key Phrases to Use:
1. "Complete software system, not just code"
2. "Requirements through deployment"
3. "Six UML diagrams showing multiple perspectives"
4. "Formal OCL specifications enforced at runtime"
5. "Database persistence with normalized schema"
6. "Forty-four tests, all passing"
7. "Professional software engineering work"

---

## RECORDING WORKFLOW

```
1. Run practice_demo.sh (2-3 times)
2. Read VIDEO_DEMO_SCRIPT.md (understand timing)
3. Set up recording (terminal + VS Code + browser)
4. Start recording
5. Follow QUICK_DEMO_COMMANDS.md
6. Stop recording
7. Review (audio OK? readable? 5 minutes?)
8. Submit!
```

---

## YOU GOT THIS

You built:
- 4,011 lines of production code
- 3,453 lines of documentation
- 6 UML diagrams
- 44 passing tests
- Complete engineering artifacts

**This is professional work. Show it with confidence.**

---

## QUICK START (Right Now)

```bash
cd /Users/yahyamounadi/Desktop/Soen-342
./practice_demo.sh
```

Then open `VIDEO_DEMO_SCRIPT.md` and read through it.

**Good luck!**

