# pi7600

Dart library for SIM7600-series 4G modems (for example the Waveshare
SIM7600G-H). It provides:

- `At` — serialized AT command client with timeout and error handling.
- `SerialTransport` / `LibSerialPortTransport` — stream-based serial I/O through
  `libserialport`; the reader runs in a separate isolate.
- `ModemSettings` — PDU mode, character set, clock, and timezone helpers.
- `Sms` / `SmsParser` — PDU and text-mode SMS reading, sending, and deletion.
- `Gps` — GPS session management and position queries.
- `Phone` — call control helpers.

The library is used by the [Pi7600 service](https://github.com/dazemc/pi7600)
but has no dependency on Serverpod or the service.

## Legacy Python implementation

This branch (`main`) contains the Dart implementation. The previous Python
implementation remains on the `master` branch.

## Requirements

- Dart **3.13** or a compatible SDK.
- Linux with `libserialport` (`libserialport0` on Debian/Ubuntu).
- A SIM7600-series modem on a serial port such as `/dev/ttyUSB2`.

On Debian, the runtime package ships `libserialport.so.0` but not the
unversioned `.so` symlink. Set:

```bash
export LIBSERIALPORT_PATH=libserialport.so.0
```

## Usage

Add the package as a path dependency (the Pi7600 service includes it as a git
submodule at `pi7600/`):

```yaml
dependencies:
  pi7600:
    path: ../pi7600
```

```dart
import 'package:pi7600/pi7600.dart';

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

  final sms = Sms(modem);
  final messages = await sms.receiveMessages();
  print('${messages.length} message(s) on the SIM');

  final gps = Gps(modem);
  print(await gps.getGpsPosition());

  await modem.close();
}
```

Call `ModemSettings.initialize()` before using SMS or GPS. It opens the serial
port and loads the modem's PDU mode, clock, and timezone.

## Testing

```bash
dart pub get
dart test
```

The tests use `FakeTransport` from `package:pi7600/testing.dart` and do not
require a modem:

```dart
import 'package:pi7600/pi7600.dart';
import 'package:pi7600/testing.dart';

final transport = FakeTransport();
final at = At(
  com: '/dev/fake',
  baudRate: 115200,
  transport: transport,
)..open();
```

## License

MIT — see [LICENSE](LICENSE).
