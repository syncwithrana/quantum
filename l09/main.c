#include "../platform/mps2_an385.h"
#include "delay.h"

unsigned fact(unsigned n) {
  if (n == 0) {
    return 1;
  } else {
    return n * fact(n - 1);
  }
}

int main(void) {
  int result = fact(5);
  return 0;
}