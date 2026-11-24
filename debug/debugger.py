
#!/usr/bin/env python3

import argparse
import cmd
import json
import os
import queue
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time


class GDB:
    """Minimal GDB/MI2 client."""

    def __init__(self, executable, elf):
        self.process = subprocess.Popen(
            [
                executable,
                "--quiet",
                "--nx",
                "--interpreter=mi2",
                elf
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        self.lines = queue.Queue()
        self.lock = threading.Lock()
        self.token = 0

        self.reader = threading.Thread(
            target=self._reader,
            daemon=True
        )
        self.reader.start()

    def _reader(self):
        for line in self.process.stdout:
            line = line.rstrip("\r\n")

            # Asynchronous execution events.
            if line.startswith("*stopped"):
                print("\n[target stopped]")
                sys.stdout.flush()
            elif line.startswith("*running"):
                print("\n[target running]")
                sys.stdout.flush()
            else:
                self.lines.put(line)

        self.lines.put(None)

    def execute(self, command):
        with self.lock:
            self.token += 1
            token = self.token

            self.process.stdin.write(
                f"{token}{command}\n"
            )
            self.process.stdin.flush()

            output = []

            while True:
                line = self.lines.get(timeout=30)

                if line is None:
                    raise RuntimeError("GDB terminated.")

                if line.startswith(f"{token}^"):
                    result = line[len(str(token)) + 1:]

                    if result.startswith("error"):
                        raise RuntimeError(
                            self._extract_message(result)
                        )

                    return output, result

                if line.startswith(('~"', '&"', '@"')):
                    try:
                        output.append(
                            json.loads(line[1:])
                        )
                    except ValueError:
                        pass

    @staticmethod
    def _extract_message(result):
        match = re.search(r'msg="((?:[^"\\]|\\.)*)"', result)

        if match:
            try:
                return json.loads('"' + match.group(1) + '"')
            except ValueError:
                pass

        return result

    def console(self, command):
        output, _ = self.execute(
            "-interpreter-exec console "
            + json.dumps(command)
        )

        text = "".join(output)

        if text:
            print(text, end="" if text.endswith("\n") else "\n")

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()

            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


class Debugger(cmd.Cmd):

    intro = """
========================================
          M3 DEBUGGER 0.1
          MPS2-AN385
========================================

Type 'help' to see available commands.
"""

    prompt = "inspect> "

    def __init__(self, gdb):
        super().__init__()
        self.gdb = gdb

    def execute(self, command):
        try:
            self.gdb.console(command)
        except Exception as e:
            print(f"Error: {e}")

    def do_run(self, arg):
        """Start/resume firmware execution."""
        self.execute("-exec-continue")

    def do_continue(self, arg):
        """Continue execution."""
        self.execute("-exec-continue")

    def do_halt(self, arg):
        """Halt the target."""
        try:
            self.gdb.execute("-exec-interrupt --all")
        except Exception as e:
            print(f"Error: {e}")

    def do_step(self, arg):
        """Execute one instruction."""
        try:
            self.gdb.execute("-exec-step-instruction")
        except Exception as e:
            print(f"Error: {e}")

    def do_next(self, arg):
        """Step over one instruction."""
        try:
            self.gdb.execute("-exec-next-instruction")
        except Exception as e:
            print(f"Error: {e}")

    def do_regs(self, arg):
        """Display CPU registers."""
        self.execute("info registers")

    def do_reg(self, arg):
        """Display a specific register. Example: reg r0"""
        if not arg.strip():
            print("Usage: reg <register>")
            return

        self.execute(f"info registers {arg.strip()}")

    def do_mem(self, arg):
        """
        Examine memory.
        Usage: mem <address> [count]
        Example: mem 0x20000000 8
        """

        try:
            args = shlex.split(arg)

            if not args:
                raise ValueError()

            address = int(args[0], 0)
            count = int(args[1], 0) if len(args) > 1 else 1

            if count < 1 or count > 256:
                raise ValueError("Count must be 1-256.")

            self.execute(f"x/{count}wx 0x{address:X}")

        except (ValueError, IndexError):
            print("Usage: mem <address> [count]")

    def do_write(self, arg):
        """
        Write memory.
        Usage: write <address> <value> [8|16|32]
        """

        try:
            args = shlex.split(arg)

            if len(args) not in (2, 3):
                raise ValueError()

            address = int(args[0], 0)
            value = int(args[1], 0)
            width = int(args[2], 0) if len(args) == 3 else 32

            types = {
                8: "unsigned char",
                16: "unsigned short",
                32: "unsigned int"
            }

            if width not in types:
                raise ValueError("Width must be 8, 16 or 32.")

            if not 0 <= value < (1 << width):
                raise ValueError("Value does not fit width.")

            self.execute(
                f"set {{{types[width]}}}0x{address:X} = "
                f"0x{value:X}"
            )

        except (ValueError, IndexError):
            print("Usage: write <address> <value> [8|16|32]")

    def do_break(self, arg):
        """
        Set breakpoint.
        Examples: break main
                  break 0x100
        """

        if not arg.strip():
            print("Usage: break <symbol/address>")
            return

        location = arg.strip()

        try:
            address = int(location, 0)
            location = f"*0x{address:X}"
        except ValueError:
            pass

        self.execute(f"break {location}")

    def do_delete(self, arg):
        """Delete breakpoint by number."""
        if not arg.strip():
            print("Usage: delete <breakpoint-number>")
            return

        self.execute(f"delete {arg.strip()}")

    def do_disasm(self, arg):
        """
        Disassemble instructions.
        Usage: disasm <address>
        """

        if not arg.strip():
            print("Usage: disasm <address>")
            return

        self.execute(f"x/12i {arg.strip()}")

    def do_stack(self, arg):
        """Display stack contents."""
        self.execute("x/16wx $sp")

    def do_bt(self, arg):
        """Display call stack."""
        self.execute("backtrace")

    def do_info(self, arg):
        """GDB information commands. Example: info breakpoints"""
        if not arg.strip():
            print("Usage: info <topic>")
            return

        self.execute(f"info {arg}")

    def do_quit(self, arg):
        """Exit debugger."""
        return True

    def do_exit(self, arg):
        """Exit debugger."""
        return True

    def do_EOF(self, arg):
        print()
        return True

    def default(self, line):
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands.")
    
    def do_clear(self, arg):
        """Clear terminal screen."""
        print("\033[2J\033[H", end="", flush=True)


def wait_for_port(port, process, timeout=5):
    start = time.time()

    while time.time() - start < timeout:

        if process.poll() is not None:
            raise RuntimeError("QEMU terminated unexpectedly.")

        try:
            with socket.create_connection(
                ("127.0.0.1", port), timeout=0.1
            ):
                return
        except OSError:
            time.sleep(0.05)

    raise RuntimeError("QEMU GDB port not responding.")

def main():

    parser = argparse.ArgumentParser(
        description="MPS2-AN385 Cortex-M3 Debugger"
    )

    parser.add_argument("--elf", required=True)
    parser.add_argument("--machine", default="mps2-an385")
    parser.add_argument("--qemu", default="qemu-system-arm")
    parser.add_argument("--gdb", default="arm-none-eabi-gdb")
    parser.add_argument("--target", default=":1234")

    args = parser.parse_args()

    port = int(args.target.rsplit(":", 1)[-1])

    qemu = None
    gdb = None

    try:
        print("Starting QEMU...")

        qemu = subprocess.Popen(
            [
                args.qemu,
                "-M", args.machine,
                "-display", "none",
                "-serial", "null",
                "-monitor", "none",
                "-S",
                "-gdb", f"tcp:127.0.0.1:{port}",
                "-kernel", args.elf
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

        wait_for_port(port, qemu)

        print("QEMU started.")
        print("Starting GDB...")

        gdb = GDB(args.gdb, args.elf)

        print("Connecting to target...")

        _, result = gdb.execute(
            f"-target-select remote localhost:{port}"
        )

        if not result.startswith("connected"):
            raise RuntimeError(
                f"Unexpected GDB connection result: {result}"
            )

        gdb.execute("-gdb-set pagination off")
        gdb.execute("-gdb-set confirm off")

        print("Target connected and halted.")

        debugger = Debugger(gdb)
        debugger.cmdloop()

    except KeyboardInterrupt:
        print("\nCtrl+C received. Shutting down...")

    except Exception as e:
        print(f"\nDebugger error: {e}")

    finally:
        print("Cleaning up...")

        if gdb:
            gdb.close()

        if qemu and qemu.poll() is None:
            qemu.terminate()

            try:
                qemu.wait(timeout=3)
            except subprocess.TimeoutExpired:
                qemu.kill()
                qemu.wait()

        print("Debugger exited.")


if __name__ == "__main__":
    main()
