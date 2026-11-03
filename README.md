# simcom_modem

A Dart library for SIMCom AT modems, built and tested with the SIM7600-series
4G modules (including the Waveshare SIM7600G-H). It covers the modem layer:
serial transport, AT commands, modem settings, SMS/PDU, GPS, and voice-call
control.

The library has no dependency on Serverpod, Flutter, or a particular
application. It runs on the Dart VM on Linux and is used by the
[SIMCom API service](https://github.com/dazemc/simcom_api).

## Features

- Stream-based serial I/O through `libserialport`; reads run on a dedicated
  isolate so the event loop is never blocked by the serial port.
- Serialized AT commands with timeouts and consistent `ERROR` handling.
- SMS in PDU and text modes: receive, send, delete, multipart messages, GSM
  7-bit and UCS-2 text, and service-centre timestamps.
- Modem settings: PDU mode, character set, clock, and timezone.
- GPS session management and position queries.
- Voice-call helpers: dial, hang up, and list active calls.
- A hardware-free `FakeTransport` for tests through
  `package:simcom_modem/testing.dart`.

## Requirements

- Dart SDK **3.13** or a compatible `^3.12.2` SDK.
- Linux with `libserialport` (`libserialport0` on Debian/Ubuntu).
- A SIMCom modem on a serial port, typically `/dev/ttyUSB2`.
- Permission to access the serial port, usually through the `dialout` group.

On Debian/Ubuntu, the runtime package ships `libserialport.so.0` but not the
unversioned `.so` symlink. Point the FFI loader at the versioned library:

```bash
export LIBSERIALPORT_PATH=libserialport.so.0
```

## Installation

The package is not published on pub.dev. Add it as a path dependency:

```yaml
dependencies:
  simcom_modem:
    path: ../simcom_modem
```

Or depend on the Git repository directly:

```yaml
dependencies:
  simcom_modem:
    git:
      url: https://github.com/dazemc/simcom_modem.git
      ref: main
```

If the repository is vendored as a git submodule, initialize it first:

```bash
git submodule update --init --recursive
```

## Quick start

```dart
import 'package:simcom_modem/simcom_modem.dart';

Future<void> main() async {
  final transport = LibSerialPortTransport(
    name: '/dev/ttyUSB2',
    baudRate: 115200,
  );
  final at = At(
    com: '/dev/ttyUSB2',
    baudRate: 115200,
    transport: transport,
  );
  final modem = ModemSettings(at: at);

  await modem.initialize();
  try {
    final response = await modem.sendAt('AT+CSQ', 'OK');
    print(response);

    final gps = Gps(modem);
    print(await gps.getGpsPosition());
  } finally {
    await modem.close();
  }
}
```

`ModemSettings.initialize()` opens the serial port and loads the modem's PDU
mode, clock, and timezone. Call it before using SMS or GPS.

## Usage

### AT commands

`At` serializes every command exchange. Use `sendAt` when the response has a
known terminator, or `sendRaw` for an arbitrary command:

```dart
final at = At(
  com: '/dev/ttyUSB2',
  baudRate: 115200,
  transport: LibSerialPortTransport(
    name: '/dev/ttyUSB2',
    baudRate: 115200,
  ),
);

at.open();
final info = await at.sendRaw('ATI');
if (At.isError(info)) {
  throw StateError('Modem did not answer: $info');
}
print(info);
at.closeSerial();
```

Timeouts and modem failures are returned as strings containing `ERROR` (or as
an empty string). Always use `At.isError`:

```dart
final response = await modem.sendAt('AT+CPIN?', 'READY');
if (At.isError(response)) {
  throw StateError('SIM is not ready: $response');
}
```

### SMS

```dart
final sms = Sms(modem);

final messages = await sms.receiveMessages();
for (final message in messages) {
  print('${message.messageOriginatingAddress}: ${message.messageContents}');
}

final sent = await sms.sendMessage('+15551234567', 'Hello from Dart');
if (!sent) {
  print('The modem rejected the message');
}

final deleted = await sms.deleteMessage(1);
```

`Sms.receiveMessages()` switches the modem to PDU mode and restores the
previous mode. `sendMessage()` uses text mode and also restores the previous
mode. `deleteMessage()` takes the modem index (`messageIndex`), not a database
id.

For raw parsing without sending commands:

```dart
final parser = SmsParser(timezone: modem.timezone);
final messages = parser.parsePdu(rawModemResponse);
```

### GPS

```dart
final gps = Gps(modem);

final position = await gps.getGpsPosition();
if (position == null) {
  print('GPS is unavailable');
} else {
  print(position);
}
```

`getGpsPosition()` checks the current GPS session, starts it when necessary,
and stops it if the query fails. A modem with an active session but no satellite
fix returns `GPS is active but no signal was found`.

### Phone control

```dart
final phone = Phone(modem);

final calls = await phone.activeCalls();
print(calls);

final connected = await phone.call('+15551234567');
if (!connected) {
  print('Call failed');
}

await phone.hangupCall();
```

### Modem settings

`ModemSettings` wraps the commands used to configure and inspect the modem:

```dart
await modem.initialize();

final pduMode = await modem.getDataMode();
final config = await modem.getConfig();
final simReady = await modem.simReadyCheck();

await modem.setSmsStorage('SM');
await modem.setEncodingMode(2); // UCS2
```

## API overview

| Type | Purpose |
| --- | --- |
| `At` | AT command client, timeouts, error detection, serialized exchanges |
| `SerialTransport` | Transport interface for custom backends and test fakes |
| `LibSerialPortTransport` | `libserialport` transport with an isolate reader |
| `ModemSettings` | PDU mode, character set, clock, timezone, and modem helpers |
| `Sms` | Receive, send, and delete SMS messages |
| `SmsParser` | Decode text-mode and PDU-mode SMS buffers |
| `ParsedMessage` | A decoded SMS message, independent of storage |
| `Gps` | GPS session management and position queries |
| `Phone` | Dial, hang up, and inspect active calls |
| `FakeTransport` | Hardware-free `SerialTransport` for tests |

## Design notes

- **One command at a time.** `At` uses an async lock so concurrent callers
  cannot interleave command writes and reads.
- **No polling.** `LibSerialPortTransport` publishes received byte chunks on a
  broadcast stream. `At` subscribes to that stream and waits for data or a
  timeout.
- **Blocking reads stay off the event loop.** `SerialPortReader` reads the
  native port in a dedicated isolate.
- **Mode changes are temporary.** SMS receive and send operations restore the
  modem's previous PDU/text mode.
- **Modem state is explicit.** `ModemSettings.initialize()` loads PDU mode,
  datetime, and timezone; do not assume those values before it runs.
- **Parsing is pure Dart.** PDU decoding, GSM 7-bit unpacking, UCS-2 decoding,
  timestamps, and multipart headers are implemented in `SmsParser`.

## Testing

The package includes a hardware-free transport for tests:

```dart
import 'package:simcom_modem/simcom_modem.dart';
import 'package:simcom_modem/testing.dart';
import 'package:test/test.dart';

void main() {
  test('reads the signal quality', () async {
    final transport = FakeTransport()
      ..onCommand = (command, fake) {
        if (command.startsWith('AT+CSQ')) {
          fake.emit('\r\n+CSQ: 20,99\r\nOK\r\n');
        }
      };
    final at = At(
      com: '/dev/fake',
      baudRate: 115200,
      transport: transport,
    )..open();

    final response = await at.sendAt('AT+CSQ', 'OK', 1);

    expect(At.isError(response), isFalse);
    expect(response, contains('+CSQ: 20,99'));
    at.closeSerial();
    await transport.dispose();
  });
}
```

Run the suite with:

```bash
dart pub get
dart test
```

No modem, SIM card, or serial port is required; install `libserialport` as
described in [Requirements](#requirements).

## Compatibility

The library is tested with the SIM7600G-H. Other SIMCom AT modems should work
when they support the same AT command set; the SMS, GPS, and call helpers are
thin wrappers around those commands.

`LibSerialPortTransport` is Linux-specific because it uses `libserialport`
through FFI. Other platforms can provide their own `SerialTransport`
implementation.

## License

MIT — see [LICENSE](LICENSE).
