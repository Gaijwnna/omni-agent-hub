# Source protection and GitHub handoff

## What can be protected

Keep service implementation, scoring operations, signing keys, customer data and unpublished benchmark evidence in a **private repository**. Deploy only the container image or server runtime; never serve the repository directory. Keep browser-delivered assets minimal. Put credentials in a secret manager; restrict who can change release workflows, scoring versions and billing code.

The root proprietary notice reserves rights in protectable source and content, without pretending to own public datasets or dependencies. It does not prevent independent implementation of a similar idea, establish patent rights, or guarantee copyright in wholly AI-generated work. Confirm the actual owner, contributor agreements and human authorship with a qualified adviser. Public HTML and exposed API behaviour can always be observed. Do not sabotage copying, interfere with a visitor's device, or add hostile code as a protection measure.

For reproducibility, publish the benchmark specification and methodology, not secrets. The current licence remains proprietary; the project should not describe its source as “open source”. An “open benchmark” can mean an openly documented and accessible evaluation, but must state the exact reuse rights. If you later release the SDK or suite under a permissive licence, grant that permission only for those isolated packages.

## GitHub facts from this session

The connected account returned no accessible repositories. The connector supports file creation in an existing repository, but exposes no repository-creation operation. No GitHub file, repository, branch or PR has been created. No source has been made public.

To complete the handoff, create or select an empty private repository (for example `omni-agent-hub-private`), grant the GitHub connection access, and provide its URL. The prepared source includes `.github/workflows/quality.yml`, a proprietary `LICENSE`, `.gitignore`, pinned dependencies and tests. The existing Sites source remote is separate from your GitHub account and should not be confused with a new GitHub repository.

Recommended repository settings: private visibility, minimum collaborators, protected default branch, required tests/reviews, disabled untrusted workflow write permissions, secret scanning where available, private container registry and audited deploy credentials. Do not publish backend source just to publish a thin client SDK.

## References

- GOV.UK copyright overview: https://www.gov.uk/copyright
- GitHub licensing guidance, including public view/fork rights: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

Update: private repository created at https://github.com/Gaijwnna/omni-agent-hub-private. Browser verified the Private label. Connector returned 404 for the new private repository; browser upload is used for the release archive. Branch protections and connector access have not been changed.
