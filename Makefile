CC = gcc
PYTHON ?= python3
CPPFLAGS += -Iinclude -D_POSIX_C_SOURCE=200809L
CFLAGS ?= -std=c99 -Wall -Wextra -g
LDLIBS = -pthread -lm
CUNIT_LIBS = -lcunit

FOLLOWER_SRCS = follower event tpnet emergency intruder cruise_control matrix_clock
FOLLOWER_OBJS = $(addprefix build/,$(addsuffix .o,$(FOLLOWER_SRCS)))
LEADER_OBJS = build/leader.o build/matrix_clock.o build/event.o
TEST_BINS = bin/heartbeat_test bin/test_matrix_clock bin/test_cruise_control bin/test_intruder bin/test_leader_integration

.PHONY: all clean test test-binaries test-heartbeat test-matrix-clock test-cruise-control test-intruder test-leader-integration test-python prepare-runtime help

all: bin/leader bin/follower

bin/leader: $(LEADER_OBJS)
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $^ $(LDLIBS) -o $@

bin/follower: $(FOLLOWER_OBJS)
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $^ $(LDLIBS) -o $@

build/%.o: src/%.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

build/tests/%.o: tests/%.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -MMD -MP -c $< -o $@

build/leader_test.o: src/leader.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -DTEST_LEADER -MMD -MP -c $< -o $@

bin/heartbeat_test: build/tests/heartbeat_test.o
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $^ $(CUNIT_LIBS) -o $@

bin/test_matrix_clock: build/tests/test_matrix_clock.o build/matrix_clock.o
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $^ $(CUNIT_LIBS) -o $@

bin/test_cruise_control: build/tests/test_cruise_control.o build/tests/support/cruise_fixture.o build/cruise_control.o build/matrix_clock.o
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $^ $(CUNIT_LIBS) $(LDLIBS) -o $@

bin/test_intruder: build/tests/test_intruder.o build/tests/support/intruder_fixture.o build/intruder.o build/matrix_clock.o build/event.o
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $^ $(CUNIT_LIBS) $(LDLIBS) -o $@

bin/test_leader_integration: build/tests/test_leader_integration.o build/leader_test.o build/event.o build/matrix_clock.o
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $^ $(LDLIBS) -o $@

test-binaries: $(TEST_BINS)

test: test-binaries
	$(PYTHON) scripts/run_tests.py

test-heartbeat: bin/heartbeat_test
	./$<

test-matrix-clock: bin/test_matrix_clock
	./$<

test-cruise-control: bin/test_cruise_control
	./$<

test-intruder: bin/test_intruder
	./$<

test-leader-integration: bin/test_leader_integration
	$(PYTHON) scripts/run_tests.py test_leader_integration

test-python:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

prepare-runtime:
	$(PYTHON) scripts/prepare_runtime.py

clean:
	rm -f build/*.o build/*.d build/tests/*.o build/tests/*.d build/tests/support/*.o build/tests/support/*.d bin/leader bin/follower $(TEST_BINS)

help:
	@printf '%s\n' 'make                   Build bin/leader and bin/follower (Linux/WSL)' 'make test              Run all C suites and Python checks; reports all failures' 'make test-heartbeat    Run heartbeat model tests' 'make test-matrix-clock Run matrix clock unit tests' 'make test-cruise-control Run original cruise assertions (known failures)' 'make test-intruder     Run isolated intruder helper tests' 'make test-leader-integration Run socketpair-based integration scenario' 'make test-python       Check bridge, runtime setup, and notebook syntax' 'make prepare-runtime  Create log and intruder files without overwriting data' 'make clean            Remove generated build files; preserve runtime data'

-include $(wildcard build/*.d build/tests/*.d build/tests/support/*.d)
