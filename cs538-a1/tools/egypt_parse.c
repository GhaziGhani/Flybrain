/*
 * egypt_parse.c - stand-in for the course's simple_bgp_parse.c
 *
 * Reads `bgpdump -m` output on stdin: a RIB dump first, then update files.
 *   - RIB entries (TABLE_DUMP / TABLE_DUMP2) whose ORIGIN AS (the last AS in
 *     the AS_PATH) is an Egyptian ISP mark that prefix "interesting".
 *   - Withdrawals (BGP4MP|t|W|...) of an interesting prefix bump a counter.
 *
 * Output: one line per interesting withdrawal: "<unix_time> <running_total>",
 * which can be plotted directly. A summary goes to stderr.
 *
 * Build: gcc -O2 -o egypt_parse egypt_parse.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const long EGYPT_AS[] = {5536, 8452, 24835, 24863, 36992};
#define N_EGYPT (sizeof EGYPT_AS / sizeof EGYPT_AS[0])

/* Simple open-addressing hash set of prefix strings. */
#define TABLE_SIZE (1 << 20)
static char *table[TABLE_SIZE];
static long n_interesting;

static unsigned long hash(const char *s) {
    unsigned long h = 5381;
    while (*s) h = h * 33 + (unsigned char)*s++;
    return h;
}

static int lookup(const char *p, int insert) {
    unsigned long i = hash(p) & (TABLE_SIZE - 1);
    while (table[i]) {
        if (strcmp(table[i], p) == 0) return 1;
        i = (i + 1) & (TABLE_SIZE - 1);
    }
    if (insert) { table[i] = strdup(p); n_interesting++; }
    return 0;
}

static int is_egyptian(long as) {
    for (size_t i = 0; i < N_EGYPT; i++)
        if (EGYPT_AS[i] == as) return 1;
    return 0;
}

/* Origin AS = last token of the AS path. An AS_SET like "{1,2}" is ignored. */
static long origin_as(const char *path) {
    const char *last = strrchr(path, ' ');
    last = last ? last + 1 : path;
    if (*last == '{') return -1;
    return strtol(last, NULL, 10);
}

int main(void) {
    char line[65536];
    char *f[16];
    long n_updates = 0, n_withdrawals = 0, n_hits = 0;
    long first_t = 0, last_t = 0;

    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\n")] = 0;
        int n = 0;
        char *s = line;
        while (n < 16) {
            f[n++] = s;
            s = strchr(s, '|');
            if (!s) break;
            *s++ = 0;
        }
        if (n < 6) continue;

        if (strncmp(f[0], "TABLE_DUMP", 10) == 0 && n >= 7) {
            /* f[5]=prefix, f[6]=AS path */
            if (is_egyptian(origin_as(f[6]))) lookup(f[5], 1);
        } else if (strcmp(f[0], "BGP4MP") == 0) {
            long t = atol(f[1]);
            if (!first_t) first_t = t;
            last_t = t;
            n_updates++;
            if (strcmp(f[2], "W") == 0) {
                n_withdrawals++;
                if (lookup(f[5], 0)) printf("%ld %ld\n", t, ++n_hits);
            }
        }
    }

    fprintf(stderr, "interesting (Egyptian) prefixes: %ld\n", n_interesting);
    fprintf(stderr, "update messages: %ld  (withdrawals: %ld)\n", n_updates, n_withdrawals);
    if (last_t > first_t)
        fprintf(stderr, "first=%ld last=%ld  avg rate=%.2f updates/s\n",
                first_t, last_t, (double)n_updates / (last_t - first_t));
    fprintf(stderr, "Egyptian withdrawals: %ld\n", n_hits);
    return 0;
}
