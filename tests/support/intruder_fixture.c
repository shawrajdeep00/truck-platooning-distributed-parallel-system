#include "follower.h"

/* The helper tests do not start the follower's keyboard or network threads. */
IntruderInfo current_intruder;
float current_target_gap = TARGET_GAP;

int follower_is_shutting_down(void) {
    return 1;
}

void follower_request_shutdown(const char* reason) {
    (void)reason;
}
