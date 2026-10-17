#!/usr/bin/env bash
# Runs the Android Gradle build with a JDK 21 (Capacitor 8 needs 21, Gradle 8.14 cannot run on 25).
# Uses JAVA_HOME if it is already 21, otherwise the first JDK 21 found under ~/.jdks or /usr/lib/jvm.
set -euo pipefail
cd "$(dirname "$0")/../android"
is21() { [[ -x "$1/bin/javac" ]] && "$1/bin/java" -version 2>&1 | grep -q '"21\.'; }
if [[ -z "${JAVA_HOME:-}" ]] || ! is21 "$JAVA_HOME"; then
  JAVA_HOME=""
  for d in "$HOME"/.jdks/*21* /usr/lib/jvm/*21*; do is21 "$d" && JAVA_HOME="$d" && break; done
  [[ -n "$JAVA_HOME" ]] || { echo "No JDK 21 found. Install Temurin 21 into ~/.jdks or set JAVA_HOME." >&2; exit 1; }
fi
export JAVA_HOME
exec ./gradlew "$@"
