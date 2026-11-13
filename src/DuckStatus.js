// Stable status codes; visible strings follow the shell's live language.
var states = {"loading": "Getting ready for a walk", "disabled": "Duck is disabled", "no-screen": "No display available", "locked": "Screen is locked", "display-off": "Display is off", "fullscreen": "Hidden by a fullscreen app", "paused": "Paused"};
var hints = {"loading": "Loading your pet's memory.", "disabled": "Enable Show duck under Appearance.", "no-screen": "Check your display selection under Behavior.", "locked": "Returns after you unlock the screen.", "display-off": "Returns when the display turns on.", "fullscreen": "Returns when you leave fullscreen.", "paused": "Select Resume to play."};
var reasons = {"paused": "Resume your duck first", "hidden": "Your duck is currently hidden", "locked": "Screen is locked", "disabled": "Enable your duck first", "dragging": "Put your duck down first", "not ready": "Your duck is still getting ready", "no screen": "No display available"};
function label(state,strings){return states[state]?(strings?strings.t("state."+state):states[state]):"";}
function hint(state,strings){return hints[state]?(strings?strings.t("hint."+state):hints[state]):"";}
function reason(code,strings){return strings?strings.t(reasons[code]?"reason."+code.replace(/ /g,"-"):"reason.unavailable"):(reasons[code]||"This action is currently unavailable");}
