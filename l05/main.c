#include "../platform/mps2_an385.h"
int main(void) {
  while (1) {
    FPGAIO->LED = 0x01U;
    int counter = 0;
    while (counter < 100000000) {
      ++counter;
    }
    FPGAIO->LED = 0x00U;
    counter = 0;
    while (counter < 100000000) {
      ++counter;
    }
  }
}