.PHONY: demo resume-proof eval test clean inspect-db

PYTHON ?= python3
RUN_ID ?= demo
QUESTION ?= What makes agent systems production-ready?

demo:
	$(PYTHON) -m agent_systems_proof run --run-id $(RUN_ID) --question "$(QUESTION)"

resume-proof:
	@set +e; $(PYTHON) -m agent_systems_proof run --run-id resume-proof --question "$(QUESTION)" --stop-after-step 3; code=$$?; if [ $$code -ne 75 ]; then exit $$code; fi
	$(PYTHON) -m agent_systems_proof run --run-id resume-proof --resume

eval:
	$(PYTHON) -m agent_systems_proof eval

test:
	$(PYTHON) -m unittest discover -s tests -v

inspect-db:
	sqlite3 .runs/agent.db '.tables'
	sqlite3 .runs/agent.db 'select run_id,status,current_step,total_steps from runs order by updated_at;'

clean:
	rm -rf .runs workspace traces eval_results
