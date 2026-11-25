#include "platform/mps2_an385.h"

#define LED_RED (1U << 0)
#define LED_BLUE (1U << 1)
#define LED_GREEN (1U << 2)

int main(void) {
  FPGAIO->LED &= ~(LED_RED | LED_BLUE | LED_GREEN);
  FPGAIO->LED |= LED_BLUE;
  while (1) {
    FPGAIO->LED |= LED_RED;
    int counter = 0;
    while (counter < 1000000) {
      ++counter;
    }
    FPGAIO->LED &= ~LED_RED;
    counter = 0;
    while (counter < 1000000) {
      ++counter;
    }
    int hre = 0;
  }
}