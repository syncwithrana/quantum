int main(void) {
  while (1) {
    *((unsigned int *)0x40028000U) = 0x01U;
    int counter = 0;
    while (counter < 100000000) {
      ++counter;
    }
    *((unsigned int *)0x40028000U) = 0x00U;
    counter = 0;
    while (counter < 100000000) {
      ++counter;
    }
  }
}