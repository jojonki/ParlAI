# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
import os
import time
from parlai.core.params import ParlaiParser
from parlai.mturk.core.agents import MTurkAgent, MTurkManager
from parlai.mturk.tasks.multi_agent_dialog_onboard.worlds import MTurkMultiAgentDialogTaskWorld, MTurkMultiAgentDialogOnboardWorld
from parlai.agents.local_human.local_human import LocalHumanAgent
from task_config import task_config
import copy
from itertools import product
from joblib import Parallel, delayed
import threading

"""
This task consists of one local human agent and two MTurk agents,
each MTurk agent will go through the onboarding step to provide 
information about themselves, before being put into a conversation.
You can end the conversation by sending a message ending with
`[DONE]` from human_1.
"""
def main():
    argparser = ParlaiParser(False, False)
    argparser.add_parlai_data_path()
    argparser.add_mturk_args()
    opt = argparser.parse_args()
    opt['task'] = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    opt.update(task_config)

    mturk_agent_1_id = 'mturk_agent_1'
    mturk_agent_2_id = 'mturk_agent_2'
    human_agent_1_id = 'human_1'
    mturk_agent_ids = [mturk_agent_1_id, mturk_agent_2_id]
    mturk_manager = MTurkManager(
        opt=opt,
        mturk_agent_ids = mturk_agent_ids
    )
    mturk_manager.init_aws()

    try:
        mturk_manager.start_new_run()
        mturk_manager.create_hits()

        def run_onboard(mturk_agent):
            world = MTurkMultiAgentDialogOnboardWorld(opt=opt, mturk_agent=mturk_agent)
            print("here1")
            while not world.episode_done():
                print("here2")
                world.parley()
            print("here3")
            world.shutdown()

        mturk_manager.set_onboard_function(onboard_function=run_onboard)
        mturk_manager.ready_to_accept_workers()

        def check_worker_eligibility(worker):
            return True

        def get_worker_role(worker):
            return mturk_agent_ids[len(mturk_manager.worker_candidates) % len(mturk_agent_ids)]

        def run_conversation(opt, workers):
            # Create mturk agents
            mturk_agent_1 = workers[0]
            mturk_agent_2 = workers[1]

            # Create the local human agents
            human_agent_1 = LocalHumanAgent(opt=None)
            human_agent_1.id = human_agent_1_id
            
            world = MTurkMultiAgentDialogTaskWorld(opt=opt, agents=[human_agent_1, mturk_agent_1, mturk_agent_2])

            while not world.episode_done():
                world.parley()
            world.shutdown()

            return world.get_num_abandoned_agents()

        print("here4")
        mturk_manager.start_task(
            eligibility_function=check_worker_eligibility,
            role_function=get_worker_role,
            task_function=run_conversation
        )

    except:
        raise
    finally:
        mturk_manager.expire_all_unassigned_hits()
        mturk_manager.shutdown()

if __name__ == '__main__':
    main()