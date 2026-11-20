Item 1: Services and Fit Outcomes
=================================

Status: proposed changes for the first implementation step. Runtime code has
not changed. This refines step 1 of :doc:`agentic-analysis`.

Deliverable
-----------

Make the current operations callable with an explicitly supplied analyzer,
plot configuration, and output directory. Make fitting return a truthful,
structured outcome for every dataset. Existing MCP tools retain their names,
arguments, and text return type; their messages report completed, partial,
or failed attempts instead of only saying "submitted".

Implement this in three reviewable changes: fitting first, processing second,
and plotting/exports third. Each change must keep the existing expert workflow
usable. Automatic planning and the ``analyze_data`` tool follow in later steps.

State and Dependency Injection
------------------------------

Introduce an internal ``AnalysisContext`` containing:

* A ``pykingenie.KineticsAnalyzer``.
* A ``PlotSettings`` bundle containing the five XY configuration objects.
* An output directory.
* A data revision and the latest fitting outcome for each fit family.

Every new context constructs fresh mutable objects. ``server.py`` creates one
default context for the existing MCP tools. A future analysis run can create
its own context using the same class. This prepares isolation without claiming
that the legacy default context already isolates HTTP clients.

Core services receive their dependencies explicitly and never import the
default context or call decorated MCP tools. For example:

.. code-block:: python

   def fit_kinetics(analyzer, request) -> FitBatchOutcome: ...
   def fit_steady_state(analyzer, request) -> FitBatchOutcome: ...
   def align_association(analyzer, experiment_name, sensor_names, **options): ...
   def plot_kinetic_traces(analyzer, settings, output_dir, **options): ...

The tool wrapper resolves the default context, validates external arguments,
calls a service, stores its outcome, and formats the response. The service
uses resolved experiment names; conversion from legacy numeric selectors stays
at the boundary, with 1-based bounds checked explicitly.

Move the authoritative analyzer and settings into this context rather than
maintaining two independently mutable copies of state. Update the test fixture
to replace the default context once, instead of patching analyzer references
in several modules. Internal imports of the old globals are migrated together.

Fitting Execution
-----------------

The current kinetic wrapper initializes every dataset with a steady-state
fit and then submits every kinetic fit. PyKinGenie returns successful/failed
fitting objects, but the wrapper discards those lists. Steady-state submission
has no equivalent outcome list and stops at the first exception.

Proposed execution:

1. Validate the requested model/region and dataset selection before mutation.
   No datasets is a precondition error, never a successful empty batch.
2. For each selected dataset, create a private candidate copy and put it in
   a temporary analyzer containing only that dataset. Preserve the original
   dataset name as the outcome key.
3. Run the existing initialization and submission methods on that analyzer.
   Do not duplicate PyKinGenie's fitting algorithms. Preserve all existing
   model arguments, including heterogeneous-ligand grid values. Kinetic
   initialization remains an internal step, not a standalone steady-state
   result to expose to the user.
4. Retain the dependency's success/failure lists. Where initialization raises,
   record an initialization failure for this dataset and continue with others.
   Where kinetic submission suppresses an exception, report that its failure
   reason is unavailable; do not invent an exception message.
5. Validate outputs from this attempt. Required parameter values must exist
   and be finite; required curves must have finite values, expected trace
   coverage, and matching time/signal lengths. Checks depend on the fit
   region: a dissociation-only fit does not require association curves or Kd.
   Missing covariance and uncertainty estimates are separate warnings, not
   automatic rejection of an otherwise populated fit result.
6. Commit a validated candidate for a successful dataset while preserving
   the other fit family's committed outputs. On failure, remove active
   results for the attempted family so previous curves cannot masquerade as
   this attempt's output. Preserve raw fitting inputs, the other family,
   and successful results for other datasets. Do not publish a partially
   initialized candidate.

Clear the candidate's attempted-family outputs before execution as well.
This prevents old values from making a dependency no-op look successful.
Standalone steady-state submission on single-cycle data is such a no-op in
the installed library; report it as skipped/unsupported for that operation.
The same library branch can still supply preparation required by a kinetic
fit, so do not reject kinetic fitting solely because it produced no
standalone steady-state result during initialization.

Extract ``keep_fit_results`` to accept an explicit analyzer. Audit its field
list against the supported library's result-reset method, including derived
tables, bounds, and uncertainty fields; copying parameters alone is not enough
to preserve consistency. Invalidate derived combined parameter tables when
committing or clearing family results. Keep temporary initialization outputs
out of the committed steady-state family.

Outcome Contract
----------------

Use typed ``FitRequest``, ``FitDatasetOutcome``, and ``FitBatchOutcome``
models. Batch outcomes distinguish success, partial success, failure, and
all-skipped attempts. Each dataset records its status, failure stage, reason
code, available error message, and warnings. Include an attempt ID, input
revision, fit family, model, region, and normalized options in the batch.
Computational success means that the expected outputs were produced; it is
not a scientific quality judgment.

For example, an illustrative outcome for two datasets could contain:

.. code-block:: json

   {
     "attempt_id": "attempt-003",
     "data_revision": 2,
     "kind": "kinetics",
     "model": "one_to_one",
     "region": "association_dissociation",
     "options": {"linked_smax": false, "fit_sigma": false},
     "status": "partial_success",
     "datasets": [
       {"dataset": "sample A", "status": "succeeded", "warnings": []},
       {
         "dataset": "sample B",
         "status": "failed",
         "stage": "fitting",
         "reason_code": "dependency_reported_failure",
         "error_message": null,
         "warnings": ["PyKinGenie did not expose the underlying exception."]
       }
     ]
   }

Existing fitting tools return a readable summary, for example
``Kinetic fitting completed: 1 succeeded, 1 failed. Failed: sample B.``
Add ``get_fitting_outcomes(kind="kinetics")`` as a read-only tool returning
the latest structured batch, or an explicit no-attempt response. This avoids
changing existing tools from strings to objects while giving clients reliable
data about the attempt. A valid attempt in which all fits fail still returns
its full report; malformed requests remain tool errors.

Input mutation, including sensor processing or fitting-dataset regeneration,
invalidates derived fits and cached outcomes and advances the data revision.
Initially invalidate conservatively across the context; more selective
dependency tracking can follow. A fit attempt itself does not change the input
revision. Outcome queries, parameter getters, plots, and exports must agree
about which family results are currently available.

Files to Change
---------------

* Add ``analysis/context.py`` for state ownership and fresh plot settings.
* Add ``analysis/models.py`` for typed requests and outcomes.
* Add ``analysis/fitting.py`` for validation, per-dataset execution, family
  preservation, result checks, and batch assembly.
* Add ``analysis/processing.py`` for import, metadata, selection, alignment,
  subtraction, and other experiment mutations using an explicit analyzer.
* Add ``analysis/plotting.py`` for chart generation and saving with explicit
  settings and paths. Move export readers into ``analysis/exports.py``.
* Refactor ``server.py`` and the existing tool modules into context creation
  and thin adapters. Register/export the outcome reader and document it in
  ``docs/mcp-tools.rst``.
* Update ``tests/conftest.py`` for one default-context fixture. Add service
  tests for injected analyzers and retain MCP-level coverage of the wrappers.

Acceptance Checks
-----------------

* Two independent contexts never share experiments, fit results, outcomes,
  plot settings, or output files.
* Real example-data fitting produces equivalent parameters and curves before
  and after extraction for both fit families and supported regions.
* A failure during one dataset's initialization does not block another
  dataset's successful fit.
* Dependency-reported failures, empty outputs, non-finite required outputs,
  and incomplete required curves cannot become successful outcomes.
* A failed refit cannot expose the previous attempted-family result through
  parameter, curve, export, or availability tools.
* Running either fit family, including failures, preserves the other family's
  committed results and keeps cached derived tables consistent.
* Single-cycle standalone steady-state no-ops are reported accurately;
  kinetic initialization and existing single-cycle fitting still work.
* Dataset regeneration failures leave the previous valid dataset collection
  intact; successful mutations invalidate stale derived results and outcomes.
* Existing tool names, arguments, plot formats, and text return types remain
  usable. Updated message assertions check actual outcomes. MCP tests verify
  discovery, schema, errors, and serialization of the new outcome reader.

This step does not require a PyKinGenie fork: use its existing submission
methods and expose their limitations honestly. An upstream change to return
per-dataset exceptions would improve diagnostics later.
