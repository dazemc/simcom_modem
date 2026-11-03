## 0.3.0

- Add `GpsFix` parsing for `+CGPSINFO`.
- Add `Gps.getFix()` and Google Maps URLs for valid coordinates.

## 0.2.0

- Renamed the package from `pi7600` to `simcom_modem`.
- Renamed the repository to `simcom_modem`.
- The public entrypoint is now `package:simcom_modem/simcom_modem.dart`.

## 0.1.0

- Initial Dart implementation of the SIM7600 modem library.
- AT command client, stream-based serial transport, modem settings, SMS/PDU,
  GPS, phone control, and a hardware-free `FakeTransport`.
