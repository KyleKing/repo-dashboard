# VHS documentation
#
# Run with:
#  vhs < .github/assets/demo.tape
#
# Output:
#   Output <path>.gif               Create a GIF output at the given <path>
#   Output <path>.mp4               Create an MP4 output at the given <path>
#   Output <path>.webm              Create a WebM output at the given <path>
#
# Settings:
#   Set FontSize <number>           Set the font size of the terminal
#   Set FontFamily <string>         Set the font family of the terminal
#   Set Height <number>             Set the height of the terminal
#   Set Width <number>              Set the width of the terminal
#   Set LetterSpacing <float>       Set the font letter spacing (tracking)
#   Set LineHeight <float>          Set the font line height
#   Set Theme <string>              Set the theme of the terminal (JSON)
#   Set Padding <number>            Set the padding of the terminal
#   Set Framerate <number>          Set the framerate of the recording
#   Set PlaybackSpeed <float>       Set the playback speed of the recording
#
# Sleep:
#   Sleep <time>                    Sleep for a set amount of <time> in seconds
#
# Type:
#   Type[@<time>] "<characters>"    Type <characters> into the terminal with a
#                                   <time> delay between each character
#
# Keys:
#   Backspace[@<time>] [number]     Press the Backspace key
#   Down[@<time>] [number]          Press the Down key
#   Enter[@<time>] [number]         Press the Enter key
#   Space[@<time>] [number]         Press the Space key
#   Tab[@<time>] [number]           Press the Tab key
#   Left[@<time>] [number]          Press the Left Arrow key
#   Right[@<time>] [number]         Press the Right Arrow key
#   Up[@<time>] [number]            Press the Up Arrow key
#   Down[@<time>] [number]          Press the Down Arrow key
#   Ctrl+<key>                      Press the Control key + <key> (e.g. Ctrl+C)
#
# Display:
#   Hide                            Hide the subsequent commands from the output
#   Show                            Show the subsequent commands in the output

Output .github/assets/demo.gif
Set Shell bash
Set PlaybackSpeed 0.5
Set TypingSpeed 10ms

Set Theme "Catppuccin Macchiato"
Set FontFamily "Hack Nerd Font Mono"

Set FontSize 14
Set Width 1600
Set Height 1000

Hide
Type `cd ~/Developer/kyleking`  Enter  Sleep 500ms
Type `clear`  Enter
Show

# Start the TUI
Type `uv run multi-repo-view --depth 2`  Sleep 500ms  Enter
Sleep 3s

# Navigate repos
Down 2
Sleep 1s
Down 1
Sleep 1s

# Cycle filter mode
Type `f`
Sleep 1.5s
Type `f`
Sleep 1.5s
Type `f`
Sleep 1.5s
Type `f`
Sleep 1.5s

# Cycle sort mode
Type `s`
Sleep 1.5s
Type `s`
Sleep 1.5s
Type `s`
Sleep 1.5s

# Activate search
Type `/`
Sleep 500ms
Type `multi`
Sleep 2s
Ctrl+u
Sleep 500ms

# Exit search
Escape
Sleep 1s

# Select a repo to drill down
Space
Sleep 2s

# Navigate branches
Down 2
Sleep 1s
Down 1
Sleep 1s

# Go back
Escape
Sleep 1s

# Show help
Type `?`
Sleep 3s

# Close help
Escape
Sleep 1s

# Quit
Type `q`
Sleep 500ms
