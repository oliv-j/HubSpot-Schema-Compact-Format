.PHONY: test example clean

test:
	python3 -m unittest discover tests

example:
	python3 -m hscf.cli objects encode examples/objects/raw/synthetic_contact_schema.json -o examples/objects/output --object-key synthetic_contact
	python3 -m hscf.cli workflows encode examples/workflows/raw/1743507592.workflow.json -o examples/workflows/output --workflow-key 1743507592

clean:
	rm -rf examples/objects/output/*.hsp.json examples/objects/output/options examples/objects/output/parts
	rm -rf examples/workflows/output/*.hwp.json examples/workflows/output/parts
