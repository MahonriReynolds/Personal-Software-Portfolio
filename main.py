import time
import sys

def animate_printout(message: str, spinner: str, delay: float) -> None:    
    for idx in range(len(message)):
        for _ in range(len(spinner)):
            sys.stdout.write(f'\r{message[:idx]}{spinner[_ % len(spinner)]}')
            sys.stdout.flush()
            time.sleep(delay)
    sys.stdout.write(f'\r{message}')
    sys.stdout.flush()
    time.sleep(delay)
    print()

animate_printout('Hello World', '⣾⣷⣯⣟⡿⢿⣻⣽', 0.08)
animate_printout('Hello World', '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏', 0.07)
animate_printout('Hello World', '-\\|/', 0.08)
animate_printout('Hello World', '⠂-–—–-', 0.07)
animate_printout('Hello World', '┤┘┴└├┌┬┐', 0.07)
animate_printout('Hello World', '✶✸✹✺✹✷', 0.1)
animate_printout('Hello World', '☱☲☴', 0.1)
animate_printout('Hello World', '▏▎▍▌▋▊▉', 0.08)
animate_printout('Hello World', '▏▎▍▌▋▊▉▊▋▌▍▎', 0.07)






