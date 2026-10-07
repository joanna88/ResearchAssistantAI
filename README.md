# Research Assistant Agentic System

The multi-agentic system that focuses on searching information on compound or drug target and gets relevant literature on it, like bioactivity data, properties, etc. 


## How to run it

```bash
adk web
```


## Examples

Example query:
"What is known about KRAS G12C inhibitors? Show the most potent compounds in ChEMBL, check their drug-likeness, and cite the key papers."


## Design notes

### Preventing invented SMILES

An early agent version could generate a SMILES from its own knowledge when only a compound name was provided. For example, when asked *"Is sotorasib drug-like?"*, `gemini-3.5-flash-lite` generated:

`C=CC(=O)N1[C@H]2[C@@H](C3=C(C1=CC(=N3)C4=C(C=CC(=C4F)F)Cl)C(=O)N5CCN(CC5)C)C6=CC=CC=C6C2`

The SMILES was syntactically valid, so `assess_druglikeness` successfully calculated properties for it (MW 534.99, cLogP 4.66, QED 0.36). However, it represented the wrong molecule: its formula is C29H25ClF2N4O2 and contains chlorine, whereas sotorasib is C30H30F2N6O3 and contains no chlorine.

**Why this matters:** SMILES validation confirms that a molecular structure is chemically parseable; it does not confirm that the structure corresponds to the compound requested by the user. A hallucinated but valid SMILES can therefore produce plausible and confident results for the wrong molecule.

**Fix:** Both the tool description and agent instructions now explicitly prohibit generating or inferring SMILES from compound names. Without a supplied or trusted-source SMILES, the agent asks the user for one. This behavior was verified in 2/2 new sessions.

A stricter prompt initially also rejected valid SMILES surrounded by quotation marks (e.g. `"CCO"`). The instructions now explicitly treat surrounding quotes as text delimiters rather than part of the SMILES.

**Next:** Add PubChem name-to-SMILES lookup through the MCP server so compound names can be resolved against a trusted source instead of requiring the user to provide the SMILES.


### Fabricated source

An earlier prompt allowed SMILES retrieved from *"a reliable chemical database or authoritative source."* Because the agent had no compound lookup tool, it could claim that a SMILES came from an external database without actually retrieving or verifying it.

**Why this matters:** a cited source does not establish provenance unless the agent actually accessed that source. This could allow an invented SMILES to appear trustworthy.

**Fix:** while no compound lookup tool is available, only SMILES explicitly provided by the user are accepted for tool calls. Compound names or identifiers require the user to provide the SMILES.

**Next:** a PubChem name-to-SMILES lookup will allow externally sourced SMILES with tool-verifiable provenance.

## Future work