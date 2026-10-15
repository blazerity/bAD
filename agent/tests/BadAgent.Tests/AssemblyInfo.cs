using Xunit;

// ConfigStore / BadCli tests mutate BAD_CONFIG_DIR — keep suites sequential.
[assembly: CollectionBehavior(DisableTestParallelization = true)]
