#include "../platform/mps2_an385.h"

#define LED_RED   (1U << 0)
#define LED_BLUE  (1U << 1)
#define LED_GREEN (1U << 2)

void delay(int iter) {
int volatile counter;
counter = 0;
while (counter < iter) {
    ++counter;
  }
}

int main(void) {
  FPGAIO->LED &= ~(LED_RED | LED_BLUE | LED_GREEN);
  FPGAIO->LED |= LED_BLUE;
  while (1) {
    FPGAIO->LED |= LED_RED;
    delay(100000000);
    FPGAIO->LED &= ~LED_RED;
    delay(100000000);
  }
}