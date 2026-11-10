/* Synthetic "proprietary" scoring library for the native-sdk-sample fixture. */
#include <string.h>

static int mix(int h, char c) { return (h * 31 + c) & 0x7fffffff; }

int ss_score(const char *segment, int weight) {
    if (segment == 0 || weight <= 0) return -1;
    int h = 7;
    for (size_t i = 0; i < strlen(segment); i++) h = mix(h, segment[i]);
    return (h % 1000) * weight;
}

const char *ss_version(void) { return "secretsauce 3.1.4"; }
