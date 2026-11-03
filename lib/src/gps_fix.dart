/// A parsed `+CGPSINFO` fix.
class GpsFix {
  const GpsFix({
    required this.latitude,
    required this.longitude,
    this.date,
    this.time,
    this.altitude,
    this.speedKnots,
    this.courseDegrees,
  });

  final double latitude;
  final double longitude;
  final String? date;
  final String? time;
  final double? altitude;
  final double? speedKnots;
  final double? courseDegrees;

  /// Google Maps link for this fix.
  Uri get googleMapsUrl => Uri.https('www.google.com', '/maps/search/', {
    'api': '1',
    'query': '$latitude,$longitude',
  });

  Map<String, Object?> toJson() {
    return {
      'latitude': latitude,
      'longitude': longitude,
      'date': date,
      'time': time,
      'altitude': altitude,
      'speed_knots': speedKnots,
      'course_degrees': courseDegrees,
      'maps_url': googleMapsUrl.toString(),
    };
  }
}

/// Parse a `+CGPSINFO` response into a [GpsFix].
///
/// Returns `null` for an empty/no-fix response, malformed coordinates, or a
/// response that does not contain a `+CGPSINFO:` line.
GpsFix? parseGpsInfo(String? response) {
  if (response == null || response.isEmpty) return null;

  final line = response
      .split(RegExp(r'\r\n|\n'))
      .where((value) => value.contains('+CGPSINFO:'))
      .firstOrNull;
  if (line == null) return null;

  final payload = line
      .substring(line.indexOf('+CGPSINFO:') + '+CGPSINFO:'.length)
      .trim();
  final parts = payload.split(',');
  if (parts.length < 4) return null;

  final latitude = _parseCoordinate(parts[0], parts[1], latitude: true);
  final longitude = _parseCoordinate(parts[2], parts[3], latitude: false);
  if (latitude == null || longitude == null) return null;

  return GpsFix(
    latitude: latitude,
    longitude: longitude,
    date: parts.length > 4 ? _nullIfEmpty(parts[4]) : null,
    time: parts.length > 5 ? _nullIfEmpty(parts[5]) : null,
    altitude: parts.length > 6 ? _parseDouble(parts[6]) : null,
    speedKnots: parts.length > 7 ? _parseDouble(parts[7]) : null,
    courseDegrees: parts.length > 8 ? _parseDouble(parts[8]) : null,
  );
}

double? _parseCoordinate(
  String value,
  String hemisphere, {
  required bool latitude,
}) {
  final raw = double.tryParse(value.trim());
  if (raw == null) return null;

  final degrees = raw ~/ 100;
  final minutes = raw - degrees * 100;
  if (minutes < 0 || minutes >= 60) return null;

  final direction = hemisphere.trim().toUpperCase();
  final positive = latitude ? 'N' : 'E';
  final negative = latitude ? 'S' : 'W';
  if (direction != positive && direction != negative) return null;

  final result = degrees + minutes / 60;
  if (latitude && result > 90) return null;
  if (!latitude && result > 180) return null;
  return direction == negative ? -result : result;
}

double? _parseDouble(String value) {
  final trimmed = value.trim();
  if (trimmed.isEmpty) return null;
  return double.tryParse(trimmed);
}

String? _nullIfEmpty(String value) {
  final trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}
