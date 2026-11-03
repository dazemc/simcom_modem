import 'package:simcom_modem/simcom_modem.dart';
import 'package:simcom_modem/testing.dart';
import 'package:test/test.dart';

void main() {
  late FakeTransport transport;
  late At at;
  late Phone phone;

  setUp(() {
    transport = FakeTransport();
    at = At(com: '/dev/fake', baudRate: 115200, transport: transport)..open();
    phone = Phone(ModemSettings(at: at));
  });

  tearDown(() async {
    at.closeSerial();
    await transport.dispose();
  });

  test('places a call', () async {
    transport.onCommand = (command, fake) {
      if (command.startsWith('ATD')) fake.emit('\r\nOK\r\n');
    };

    expect(await phone.call('+31612345678'), isTrue);
    expect(transport.written, contains('ATD+31612345678;\r\n'));
  });

  test('hangs up the active call', () async {
    transport.onCommand = (command, fake) {
      if (command.startsWith('AT+CHUP')) fake.emit('\r\nOK\r\n');
    };

    expect(await phone.hangupCall(), isTrue);
    expect(transport.written, contains('AT+CHUP\r\n'));
  });

  test('reads active calls', () async {
    transport.onCommand = (command, fake) {
      if (command.startsWith('AT+CLCC')) {
        fake.emit('\r\n+CLCC: 1,0,0,0,0,"+31612345678",145\r\nOK\r\n');
      }
    };

    final calls = await phone.activeCalls();

    expect(calls, isNotNull);
    expect(calls, contains('+CLCC: 1,0,0,0,0'));
  });

  test('reports modem failures', () async {
    transport.onCommand = (command, fake) {
      fake.emit('\r\nERROR\r\n');
    };

    expect(await phone.call('+31612345678'), isFalse);
    expect(await phone.hangupCall(), isFalse);
    expect(await phone.activeCalls(), isNull);
  });
}
