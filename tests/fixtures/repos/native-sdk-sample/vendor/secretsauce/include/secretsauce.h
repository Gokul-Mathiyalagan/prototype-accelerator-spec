#ifndef SECRETSAUCE_H
#define SECRETSAUCE_H

/* Score a customer segment name; higher is better. Returns -1 on bad input. */
int ss_score(const char *segment, int weight);
const char *ss_version(void);

#endif
