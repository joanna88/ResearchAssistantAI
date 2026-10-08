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

**Fix:** Both the tool description and agent instructions now explicitly prohibit generating or inferring SMILES from compound names. Without a supplied or trusted-source SMILES, the agent asks the user for one. 

A stricter prompt initially also rejected valid SMILES surrounded by quotation marks (e.g. `"CCO"`). The instructions now explicitly treat surrounding quotes as text delimiters rather than part of the SMILES.

**Next:** Add PubChem name-to-SMILES lookup through the MCP server so compound names can be resolved against a trusted source instead of requiring the user to provide the SMILES.

### Fabricated source

An earlier prompt allowed SMILES from a *"reliable chemical database or authoritative source."* The agent could exploit this ambiguity by claiming that a SMILES came from an external source without actually retrieving it.

**Why this matters:** fabricated provenance can make an invented SMILES appear verified and lead to calculations for the wrong molecule.

**Fix:** allowed external sources are now explicitly limited to PubChem and ChEMBL, and the prompt states that no connection to either database is currently available. Until lookup tools are added, the agent must ask the user to provide the SMILES.

**Next:** PubChem/ChEMBL lookup tools will provide verifiable name-to-SMILES retrieval and provenance.

### Automatic correction of misspelled compound names

Another failure mode occurred when a misspelled compound name was provided. After `lookup_compound_by_name` returned that the compound was not found and suggested checking the spelling, the LLM sometimes corrected the compound name itself and performed another lookup instead of asking the user to verify the intended compound.

**Why this matters:** automatically correcting a compound name can resolve it to a different molecule than the user intended. The lookup may then succeed, giving the incorrect correction the appearance of being verified by PubChem.

**Mitigation:** the agent instructions now explicitly state that when `lookup_compound_by_name` reports a compound as not found or potentially misspelled, the agent must not correct, reinterpret, or retry the name itself. It should instead ask the user to verify or correct the compound name.

**Fix:** a before_tool_callback blocks lookups for names that don't appear in the user's message. With the prompt alone, 1 of 4 sessions passed; with the guard, 4 of 4. It also blocks synonym substitution, as in the (S)-ibuprofen case.

**Known limitation:** PubChem's first match can be a different form of the compound, e.g. (S)-ibuprofen → the anion.

## Future work