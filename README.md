control Pi-Plates from node
# Prerequisite - you must install the python3-venv package
```
sudo apt install python3-venv
```
This is included in Raspberry Pi OS 'Bookworm' by default, but not previous releases

# Upgrading from 0.3.0 to 0.4.0

0.4.0 changes how failures are reported. In 0.3.0, if a command failed or the python
co-process crashed, the `send()` callback was never called, and every later command
was silently dropped until node was restarted. In 0.4.0:

- **Every `send()` callback is called**, including when something fails. A failure is
  reported as a reply of the form `{error: "<message>"}`, so check for it before using
  the other reply fields:

  ```js
  plate.send({cmd: "getADC", args: {channel: 0}}, (reply) => {
      if (reply.error) {
          console.log("pi-plates command failed: " + reply.error);
          return;
      }
      console.log(reply.voltage);
  });
  ```

- **The python co-process restarts itself** if it crashes, after 1s, doubling on
  repeated crashes up to 60s. Commands sent while it is restarting get an `{error}`
  reply.
- **A python exception in one command no longer kills the co-process.** That command
  gets an `{error}` reply and the next command runs as normal.
- **`shutdown()` stops the co-process without restarting it.** The next plate created
  or command sent starts it again.
- **`plate_status` no longer reflects the co-process exit code.** A plate created while
  the co-process is restarting has status 4 (unknown) until it verifies.

**Node-RED users:** upgrade node-red-contrib-pi-plates to 0.4.0 at the same time.
node-red-contrib-pi-plates 0.3.0 does not check for `{error}` replies, and with
pi-plates 0.4.0 some of its nodes (e.g. the all-ADC node) can crash Node-RED
when a command fails or the co-process restarts.
