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

### Fabricated Literature Provenance

**Problem:** The agent generates plausible scientific citations without retrieving or verifying the underlying literature, then falsely attributes them to external databases.

**Observed behavior:**

- When asked to *"cite the key papers"*, the agent provided complete references (Ostrem 2013, Canon 2019, Hallin 2020), including authors, journals, volumes, and pages, despite having no literature retrieval tool.
- When questioned about its sources, it claimed the references came from PubMed and Europe PMC, although neither had been queried.
- Similar behavior occurred when ChEMBL was unavailable, indicating a recurring tendency to substitute model-generated information for missing evidence.

**Why it matters:** Plausible citations can still have unverified metadata or fail to support the claims attached to them. Fabricated provenance creates false confidence in scientific conclusions and extends the earlier *Fabricated source* and *Preventing invented SMILES* failure patterns.

**Fix:** Implemented literature RAG using Europe PMC retrieval, Gemini embeddings, and persistent ChromaDB storage. The agent first calls `ingest_literature` to retrieve and store papers, then `search_literature` to retrieve relevant abstracts. The prompt restricts citations to papers returned by `search_literature` in the current conversation, requires abstract-level support for each cited claim, and prohibits citations from memory or false database-access claims. References contain only retrieved titles, years, and links.

**Similarity threshold decision:** No fixed similarity-score threshold is used. Semantic similarity ranks candidate papers, but citation eligibility depends on whether the retrieved abstract supports the specific statement. If no abstract provides relevant evidence, the agent must abstain rather than cite the closest match.

**Validation:** In the retrieval test, **15 of 15 citations were retrieved**, including the Ostrem paper (**PMID 24256730**), which was found through retrieval rather than recalled from model knowledge. This addresses the previously observed fabricated-provenance behavior in that test, but does not guarantee claim-level accuracy in every response. Further validation should cover unsupported claims, empty retrieval results, and database failures.

### Compressed similarity scores
Similarity scores were too compressed (0.64 off-topic vs 0.71 same-field) for a reliable fixed threshold on a small store; relevance is judged from the abstracts instead.

## Future work