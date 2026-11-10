#include "tinymath.h"

int tm_add(int a, int b) { return a + b; }

int tm_mul(int a, int b) { return a * b; }

int tm_clamp(int value, int low, int high) {
    if (value < low) return low;
    if (value > high) return high;
    return value;
}

const char *tm_version(void) { return "tinymath 1.2.0"; }
