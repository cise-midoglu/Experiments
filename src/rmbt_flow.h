/*******************************************************************************
 * Copyright 2017 Leonhard Wimmer
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *******************************************************************************/

#ifndef SRC_RMBT_FLOW_H_
#define SRC_RMBT_FLOW_H_

#include "rmbt_common.h"
#include "rmbt_result.h"

typedef struct {
	char *bind_ip, *server_host, *server_port, *cipherlist, *secret, *token, *test_id, *file_summary, *file_flows, *file_stats;
	int_fast16_t dl_num_flows, ul_num_flows, dl_duration_s, ul_duration_s, rtt_tcp_payload_num, dl_pretest_duration_s, ul_pretest_duration_s, dl_wait_time_s,
			ul_wait_time_s;
	int timeout_ms;
	bool encrypt, encrypt_debug;
} TestConfig;

typedef struct {
	TestConfig *cfg;
	pthread_t thread;
	int_fast16_t thread_num;
	pthread_barrier_t *barrier;
	struct timespec *ts_zero;
	FlowResult *flow_result;
	bool do_log;
	bool do_rtt_tcp_payload;
	bool do_uplink;
	bool do_downlink;
} ThreadArg;

void *run_test_thread_start(void *arg);

#endif /* SRC_RMBT_FLOW_H_ */