Agentic Analysis Proposal
=========================

Status: design proposal; the tools and modules below are not implemented.

The intended experience is: provide an experiment folder, archive, or loaded
experiment, say **"analyse this data"**, and receive results, diagnostic plots,
and an explanation of what the data support. The assistant should handle the
routine workflow and ask only when missing information changes the scientific
interpretation.

Recommended Architecture
------------------------

Keep the conversational agent in the MCP client. Add a deterministic,
stateful analysis runner to this server, exposed through a small set of
high-level tools. The client interprets the request and explains the results;
the server owns data validation, preprocessing, fitting, diagnostics, and the
record of every decision. This should work without a second model API key.

The analysis loop is:

.. code-block:: text

   resolve input -> inspect experiment -> build a versioned plan
       -> preprocess a working copy -> fit each eligible dataset
       -> assess diagnostics -> save report and artifacts

   Missing scientific information -> return a targeted question and run ID
       -> apply the answer -> resume from the affected stage

The runner is conditional: it selects valid processing steps, detects missing
controls, handles individual fit failures, and can conclude that an estimate
is unsupported. A fixed sequence ending in a successful optimizer return is
insufficient.

MCP already separates the host's LLM coordination from server capabilities;
see the `MCP architecture documentation
<https://modelcontextprotocol.io/docs/learn/architecture>`_. Server-side
reasoning through `MCP sampling
<https://modelcontextprotocol.io/specification/2025-11-25/client/sampling>`_
is a possible later extension, but requires client capability support. It
should not be a dependency of the first workflow.

What Exists and What Is Missing
-------------------------------

The repository already supplies most numerical and plotting operations.
The important gaps are orchestration and evidence about their outcomes:

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Area
     - Current implementation
     - Required addition
   * - Entry point
     - Separate import, preprocessing, fitting, and plotting tools.
     - One request that discovers the appropriate workflow.
   * - State
     - ``server.py`` creates one process-global ``PY_KINETICS`` and shared
       plot settings. This is not isolation between HTTP sessions.
     - An analyzer, plot configuration, and output directory per analysis run.
   * - Processing
     - Alignment and subtraction normally modify loaded experiments in place.
     - Immutable input snapshot, working copies, and a processing history.
   * - Dataset selection
     - ``initiate_fitting_datasets`` validates rows but resets existing fits;
       without a table it selects all positive-concentration rows.
     - Run-scoped selection with explicit sample, experiment, and Smax groups.
   * - Fit outcome
     - ``run_kinetics_fitting`` discards the underlying analyzer's successful
       and failed fit lists and returns a submission message.
     - Per-dataset outcomes, actual result validation, and partial results.
   * - Diagnostics
     - Parameter tables, correlation matrices, residual plots, and
       leave-one-out calculations exist as separate tools.
     - Numerical QC summaries and a versioned policy for interpreting them.
   * - Reproducibility
     - Plots are saved; analysis state lives in memory.
     - Saved input identity, plan, decisions, results, and replay instructions.

``obtain_sample_info_table`` also updates experiment metadata and the merged
table. The new inspection service must operate on a copy rather than assume
that every existing inspection wrapper is read-only.

The tool registration for ``import_kingenie_surface_csv`` is active through
its decorator when ``_pykingenie`` is imported, despite its commented entry
in ``tools/__init__.py``. Verify capabilities through MCP tool discovery,
not only through ``__all__``.

Resolving "This Data"
---------------------

The proposed ``analyze_data`` tool accepts either a server-accessible
``source`` path or explicit ``experiment_names``. With neither argument,
use the sole loaded experiment. With multiple experiments, use an explicitly
established scope from the conversation or ask which experiment to analyze.
With no loaded data, ask for the input location. Never silently load the
example or scan unrelated folders.

Resolve relative paths against the existing ``DATA_DIR``. Recognize an Octet
folder from its sensor files and metadata, a Gator folder/archive from its
channel files and INI metadata, and a KinGenie surface CSV from its columns.
Unknown or conflicting formats produce a useful input error. A chat attachment
must first be made accessible to the local server by the host; its filename
alone is not an importable path. Octet archives require an extraction adapter
because the existing Octet importer accepts folders only.

Archive extraction belongs in a fresh run directory. Validate members and
size limits, handle a single enclosing folder, and avoid overwriting another
run's input. Hash the actual files used for import and retain their manifest.

Scientific Decisions
--------------------

The initial policy should support multi-cycle surface-binding analysis with
a one-to-one kinetic model. Inspect other protocols and report their limits;
do not apply the same preprocessing to single-cycle experiments by accident.
The existing library supports more models and single-cycle fitting, but their
automatic selection needs separate validation.

.. list-table::
   :header-rows: 1
   :widths: 24 46 30

   * - Decision
     - Autonomous behavior
     - When information is needed
   * - Concentrations
     - Read instrument metadata and retain explicit units. Validate finite
       values, trace lengths, and phase availability.
     - Missing units or missing concentrations: ask for the values. Do not
       infer them from sensor ordering.
   * - References
     - Identify zero-concentration candidates within matching sample,
       loading, association, dissociation, and replicate context. Use a
       unique compatible control under the versioned policy and record why.
     - Ambiguous or absent compatible controls: ask for the control mapping
       or whether the data were already referenced.
   * - Sample selection
     - Analyze each valid sample group separately. Preserve replicates and
       existing Smax groups; keep capacity unlinked by default.
     - Ambiguous sample identities or pooling across experiments: ask before
       combining biologically different measurements.
   * - Preprocessing
     - On the working copy, align association, align dissociation, and
       subtract the matched reference only when required by the raw-data
       protocol. Record parameters and check the result.
     - Unknown processing history: establish whether the input is raw.
       Inter-step correction needs evidence for its same-well assumption.
   * - Model
     - Start with one-to-one association/dissociation fitting for eligible
       datasets. Report model assumptions and inadequacy when detected.
     - No automatic mechanistic claim or complex-model escalation in v1.
   * - Uncertainty
     - Use available parameter errors and correlations. Run leave-one-out
       sensitivity analysis when enough curves and the run budget permit.
     - Mark skipped or failed diagnostics explicitly. Do not present
       leave-one-out variability as a calibrated confidence interval.
   * - Trace quality
     - Flag drift, spikes, weak response, and inconsistent replicates.
       Preserve measured traces and distinguish invalid data from warnings.
     - No automatic outlier deletion, smoothing, or replicate averaging.

Zero concentration is evidence for a blank analyte control, not proof of an
unloaded reference surface. Preserve this distinction in the plan and report;
do not invent a double-reference correction from one control type.

For the bundled Octet example, direct inspection with PyKinGenie 1.0.20
returns 72 metadata rows, six sample labels, nine Smax groups, and nine
zero-concentration records associated with H1 across different steps and
replicates. The seven positive concentrations span 0.001 to 0.13 micromolar.
This supports discovery of H1 as a candidate but does not justify hard-coding
H1 for every experiment. The automated workflow should inspect all six groups;
the README demonstration deliberately selects only ``wt - imd``.

Diagnostics and Stopping Rules
------------------------------

Each dataset needs an independent execution outcome and scientific assessment.
Check that expected curves and finite parameters were actually produced.
Record parameter bounds, missing covariance, and correlations where available;
an optimizer return alone cannot establish identifiability.

Compute residual summaries per phase and trace, including RMSE, mean, temporal
structure, and the noise estimate used for normalization. Include baseline
drift, observed response range, and measured dissociation extent. Collect
bound information and optimizer diagnostics through an adapter when the
current result wrappers do not expose them. Mark unavailable checks as
unassessed instead of passing them.

Use versioned QC rules calibrated against synthetic truth and reviewed real
experiments. Do not ship an arbitrary correlation or RMSE cutoff as a
validated scientific acceptance criterion. Until that calibration exists,
separate measured diagnostics from provisional warnings. A report may say
"the model is inadequate" or "the parameters are poorly determined" and
still be a successfully completed analysis.

Set limits on wall time, dataset count, and leave-one-out refits before
execution. An initial proposal is one baseline model per eligible group,
at most 20 leave-one-out refits per run, and a configurable total deadline.
These are operational limits to benchmark, not scientific thresholds.
Bounded workers are required to interrupt an individual fit at its deadline;
an ``async`` wrapper around synchronous fitting does not provide cancellation.
Persist completed groups if another group fails or exhausts the budget.

Later, add residual-guided comparison against a bounded set of models.
Retain every candidate's results and compare fits using the same observations
and an explicit noise model. Lower residual error alone must not select a
more complex mechanism.

Proposed MCP Surface
--------------------

Keep the existing tools for expert use. Add four workflow tools with typed,
structured responses:

* ``analyze_data(source=None, experiment_names=None, options=None)`` creates
  and advances a run. Source and experiment names are mutually exclusive.
  Options include sample selection, control mappings, processing history,
  and resource limits. Routine decisions execute without a confirmation
  round-trip.
* ``get_analysis_status(run_id)`` returns the current stage, dataset outcomes,
  warnings, and any question that prevents further progress.
* ``resume_analysis(run_id, answers)`` validates answers against pending
  question IDs, revises the plan, and resumes only affected work.
* ``get_analysis_report(run_id)`` returns the compact scientific summary and
  artifact references, without rerunning the analysis.

Use a shared response model with ``run_id``, ``state``, ``stage``,
``plan_version``, ``datasets``, ``questions``, ``warnings``, and ``artifacts``.
Execution states are ``running``, ``needs_input``, ``completed``,
``completed_with_warnings``, and ``failed``. Per-dataset scientific assessments
are separate: ``supported``, ``provisional``, ``inconclusive``, or
``not_assessed``. Questions carry their scope, missing field, reason, and
allowed answers so the host can ask a specific question in ordinary language.

Return measured values with units and provenance. Keep full trace arrays in
artifacts instead of filling the model context with every time point. MCP
supports `structured tool results and output schemas
<https://modelcontextprotocol.io/specification/2025-11-25/server/tools>`_;
verify the public schemas and error behavior through the installed SDK's
in-process client before relying on them.

The first release can execute a bounded stage within the tool call and return
at completion or a scientific question. Pollable long-running execution needs
a supervised worker and explicit task ownership; merely returning a run ID
does not create a background job. Add that execution mode separately, with
progress, cancellation, and disconnect tests.

Run Isolation and Reproducibility
---------------------------------

Create an ``AnalysisRun`` that owns its analyzer and plot settings. For loaded
experiments, snapshot selected data before processing; for a source path,
import directly into the run's analyzer. Deep-copying the bundled Octet
experiment works in the installed library, but other importers and large
datasets need isolation and memory tests.

Extract numerical operations into services that accept an analyzer and
configuration explicitly. Existing tools remain thin wrappers around the
legacy analyzer. New workflow tools call services with the run analyzer;
do not temporarily swap ``PY_KINETICS`` or other module globals. All current
fit submission methods operate over the analyzer's fitting collection, so
per-dataset failure handling needs isolated fitting execution as well.
The underlying kinetic submission method catches exceptions without returning
their reasons. Preserve the failure list and report unavailable details
honestly, or expose the original exceptions through a library adapter/upstream
change. Preserve the existing wrapper's initialization fits and its protection
of the other fit family's results when extracting these services.

Suggested module boundaries are ``analysis/models.py`` for typed run and
response models, ``analysis/services.py`` for explicit analyzer operations,
``analysis/inspection.py`` for input and protocol checks,
``analysis/workflow.py`` for planning/execution, ``analysis/reporting.py`` for
diagnostics and artifacts, and ``tools/_analysis.py`` for MCP registration.

Save each run under ``DATA_DIR/analyses/<run_id>/`` with:

* A manifest containing input hashes, package versions, normalized units,
  selected trace identities, and the QC policy version.
* The resolved plan and an append-only history of completed operations,
  answers, fit outcomes, skipped checks, and resource-limit events.
* Machine-readable results and diagnostics, parameter/curve CSVs, raw and
  processed trace plots, fitted curves, and residual plots.
* A readable HTML or Markdown report with assumptions, exclusions, uncertainty
  method, warnings, and links to the underlying artifacts.

Key completed operations by input identity, normalized plan, and stage, so
retrying a request cannot subtract the reference twice. Write stage outputs
atomically; serialize mutations to a run. A changed source invalidates its
plan rather than silently reusing it. For loaded in-memory data without
original files, save a normalized numeric and metadata snapshot sufficient
for replay. Restart recovery rebuilds from these inputs and saved operations;
do not persist arbitrary Python objects with pickle.

Update ``build_server_instructions`` to direct broad analysis requests to the
new entry point once it exists. Remove the instruction in
``run_kinetics_fitting`` to ask about leave-one-out immediately after every
fit; the workflow's uncertainty policy and budget should determine that step.

Implementation Order and Acceptance
-----------------------------------

1. **Extract services and expose real outcomes.** Preserve current expert
   tools, inject the analyzer into processing/fitting/plotting services, and
   retain per-dataset success/failure details. Verify no-result and partial
   fits cannot be reported as successful fits. See the detailed
   :doc:`service-extraction` proposal.
2. **Add isolated inspection and planning.** Introduce the run models,
   format detection, metadata summaries, reference matching, protocol checks,
   and targeted questions. Verify inspection leaves the original experiment
   unchanged and never combines unrelated sample groups.
3. **Deliver the first end-to-end workflow.** Add the four MCP tools, the
   multi-cycle one-to-one policy, numerical diagnostics, resource limits,
   saved report, and client instructions. Verify retries, question/resume,
   and failed groups preserve valid results and raw inputs.
4. **Validate broader autonomy.** Calibrate QC, then add single-cycle
   processing, complex-model comparison, and supervised background execution
   as independently tested capabilities.

Acceptance must cover the actual natural-language experience as well as
Python calls. In a fresh supported MCP client, "analyse this data" plus a
valid input should reach the workflow tool and produce a report without the
user naming alignment or fitting tools. Record client/model versions for
these smoke tests; client instruction-following is not guaranteed by a
Python integration test.

Use the bundled Octet experiment for group/control discovery and a real
multi-cycle end-to-end run. Use the minimal Gator fixture for detection and
missing-control behavior rather than assume it is a complete assay. Use the
simulation CSV to compare against known parameters and the single-cycle
fixture to verify that the multi-cycle policy declines inappropriate steps.
Add deliberately ambiguous controls, missing concentrations, flat signals,
partial fit failures, and two simultaneous runs. Demonstrate that a failure
cannot alter another run, earlier results, or the raw experiment.

During this design pass, seven existing tests passed for real alignment and
subtraction, default dataset generation, experiment identity, ambiguous
selection, preservation of both fit types, correlations, and curve exports.
That verifies reusable building blocks, not an autonomous workflow. The
implementation above remains future work.
