import 'package:simcom_modem/simcom_modem.dart';
import 'package:test/test.dart';

void main() {
  test('parses a valid fix and builds a Maps URL', () {
    final fix = parseGpsInfo(
      '+CGPSINFO: 1234.5678,N,12345.6789,W,031126,120000.00,12.3,0.5,90.0',
    );

    expect(fix, isNotNull);
    expect(fix!.latitude, closeTo(12.57613, 0.00001));
    expect(fix.longitude, closeTo(-123.761315, 0.00001));
    expect(fix.date, '031126');
    expect(fix.time, '120000.00');
    expect(fix.altitude, 12.3);
    expect(fix.speedKnots, 0.5);
    expect(fix.courseDegrees, 90.0);
    expect(fix.googleMapsUrl.host, 'www.google.com');
    final coordinates = fix.googleMapsUrl.queryParameters['query']!.split(',');
    expect(double.parse(coordinates[0]), closeTo(fix.latitude, 0.000001));
    expect(double.parse(coordinates[1]), closeTo(fix.longitude, 0.000001));
  });

  test('returns null for no fix or missing data', () {
    expect(parseGpsInfo(null), isNull);
    expect(parseGpsInfo(''), isNull);
    expect(parseGpsInfo('+CGPSINFO: ,,,,,,,,'), isNull);
    expect(parseGpsInfo('GPS is active but no signal was found'), isNull);
  });

  test('rejects malformed coordinates', () {
    expect(parseGpsInfo('+CGPSINFO: 1260.0000,N,12345.6789,W,,,,,,'), isNull);
    expect(parseGpsInfo('+CGPSINFO: 1234.5678,X,12345.6789,W,,,,,,'), isNull);
    expect(parseGpsInfo('+CGPSINFO: 1234.5678,N,12345.6789,N,,,,,,'), isNull);
  });

  test('parses south and east coordinates', () {
    final fix = parseGpsInfo('+CGPSINFO: 1234.5678,S,12345.6789,E,,,,,,');

    expect(fix, isNotNull);
    expect(fix!.latitude, lessThan(0));
    expect(fix.longitude, greaterThan(0));
  });
}
