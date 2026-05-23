.PHONY: test example clean

test:
	python -m unittest discover tests

example:
	python -m hscf.cli encode examples/raw/synthetic_contact_schema.json -o examples/output --object-key synthetic_contact

clean:
	rm -rf examples/output/*.hsp.json examples/output/options examples/output/parts
