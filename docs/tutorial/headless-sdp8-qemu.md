# QNX SDP 8.0 on a headless Linux server: install, boot an x86_64 target in QEMU, run your first program

*Draft, 2026-11-15. Written from a real install on an Ubuntu x86_64 server with no desktop and no root/sudo for QEMU. Every command below was run; where it failed the first time, the failure is shown with the fix.*

**You will end with:** QNX SDP 8.0 installed under your home directory, a QNX 8.0 x86_64 image booting in QEMU (with KVM if available), and a C program you cross-compiled with `qcc` printing on the target.

**What you need:** a myQNX account with a Non-Commercial license, an x86_64 Linux machine you can SSH into, ~10 GB free disk.

---

## 1. Get the license into a state the installer accepts

1. myQNX → License Manager → **Accept License** for «QNX SDP 8.0 Non-Commercial».
2. Same row → **Users** → deploy it to your own email. (Until it is deployed, the command-line installer finds no license.)

## 2. Install the Software Center without a GUI

Download the Linux Software Center installer (`qnx-setup-*-linux.run`) on any machine with a browser and copy it to the server. Then:

```bash
sh qnx-setup-2.0.4-*-linux.run --noexec --keep --target sc_stage
cd sc_stage && bash start.sh -y -d -t ~/qnx        # -y accept EULA, -d don't auto-start the GUI
```

## 3. Install SDP 8.0 from the command line — four traps, in order

Use `~/qnx/qnxsoftwarecenter/qnxsoftwarecenter_clt`. Pass your myQNX user/password on each call (read the password with `read -s`, don't put it in shell history).

| Step | Command | If you skip or change this step | Do this |
|---|---|---|---|
| a | `-syncLicenseKeys` | — | pulls your deployed license |
| b | `-activateLicenseKey <KEY>` | install later fails with «License key is not activated» | activate explicitly; `-listLicenseKeys` shows the key |
| c | `-mirror` | `-installBaseline` alone fails: «Cannot find anything in local repository» · `-mirrorBaseline` leaves out target packages («requires com.qnx.qnx800.target … could not be found») | mirror **everything** with `-mirror` |
| d | `-installBaseline com.qnx.qnx800 -destination ~/qnx/qnx800` | the baseline is **not** `com.qnx.sdp/8.0` («Cannot find com.qnx.sdp/8.0») | list ids with `-offline -list` and use `com.qnx.qnx800` |

Check it:

```bash
source ~/qnx/qnx800/qnxsdp-env.sh
printf '#include <stdio.h>\nint main(){puts("hello qnx");return 0;}\n' > hello.c
qcc -Vgcc_ntox86_64 -o hello hello.c && file hello     # ELF 64-bit … interpreter /usr/lib/ldqnx-64.so.2
```

## 4. QEMU without sudo

If you cannot `apt install qemu-system-x86`, download the `.deb` packages and unpack them into a folder (`dpkg -x`), then point QEMU at its own modules and libraries:

```bash
export QEMU_MODULE_DIR=$ROOT/usr/lib/x86_64-linux-gnu/qemu
export LD_LIBRARY_PATH=$ROOT/usr/lib/x86_64-linux-gnu
$ROOT/usr/bin/qemu-system-x86_64 -L $ROOT/usr/share/qemu …
```

Traps: missing shared library → unpack the dependency `.deb` too; «accelerator not found / TCG module» → set `QEMU_MODULE_DIR`; BIOS file not found → `-L $ROOT/usr/share/qemu`. KVM: ask an admin once for `sudo usermod -aG kvm $USER`, then add `-enable-kvm`.

## 5. Build an image, put your program in it, boot

```bash
mkdir vm && cd vm
mkqnximage --type=qemu --arch=x86_64 --ssh-ident=none --noprompt
printf '[perms=0755] /var/hello=%s/../hello\n' "$PWD" > local/snippets/data_files.custom
mkqnximage --type=qemu --arch=x86_64 --ssh-ident=none --noprompt --clean   # trap: without --clean the snippet is silently ignored ("Nothing to do")
```

Boot (serial console on stdio) and run `/var/hello` at the `#` prompt. `pidin` shows every thread's state — useful in the next step.

## 6. When it breaks: qnx-doctor (optional)

`qnx-doctor` re-runs a failing command, reads the local QNX docs index, proposes a fix as data, applies it and **re-runs to prove it**. It only reports «solved» when the re-run passes. Repo: (link at submission).

---
*Not included on purpose: any QNX performance or timing numbers (QNX Development License 4.6(i)).*
