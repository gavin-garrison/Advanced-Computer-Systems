CC=gcc
CFLAGS=-O3 -march=native -pthread -Wall -Wextra
LDFLAGS=-pthread

BIN=bench_a1

all: $(BIN)

$(BIN): bench_a1.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(BIN)
