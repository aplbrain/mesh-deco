# mesh-deco on AWS λ

You can host meshing `worker` nodes on AWS Lambda in order to scale the worker pool "infinitely". The notation for this is identical to the treatment of conventional servers, and the config file might look like this:

```json
{
    "workers": [
        {
            "url": "https://[MY UUID].execute-api.us-east-1.amazonaws.com/[MY_URL]/"
        }
    ]
}
```

It is recommended that you use [zappa](https://github.com/Miserlou/Zappa) to deploy worker nodes to Lambda endpoints. For more instructions, see [Deploying with Zappa](#deploying-with-zappa)

## Deploying with Zappa

It is recommended that you use [zappa](https://github.com/Miserlou/Zappa) to deploy worker nodes to Lambda endpoints. Zappa converts Flask servers into deployed services (public) using AWS Lambda.

Here is an example `zappa.config.json`:

```json
{
    "dev": {
        "app_function": "worker_mesh_server.App",
        "aws_region": "us-east-1",
        "profile_name": "[YOUR PROFILE]",
        "project_name": "meshdeco",
        "runtime": "python3.6",
        "s3_bucket": "mesh-worker-[YOUR RANDOM ID]",
        "slim_handler": true
    }
}
```

You must replay `YOUR PROFILE` with the name of your AWS profile, if you have multiple in your [AWS auth file](https://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html). (If you only have one profile in this file, you may omit this key-value pair.)

Note that `slim_handler` should be set to `true` to enable the installation of C libraries (required) on the Lambda node. As a result, you must specify a `s3_bucket`, for which you may provide an arbitrary string. The bucket will be created for you at runtime.
