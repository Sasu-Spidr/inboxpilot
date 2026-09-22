auto_auth {
  method "approle" {
    config = {
      role_id_file_path                   = "/bootstrap/role_id"
      secret_id_file_path                 = "/bootstrap/secret_id"
      remove_secret_id_file_after_reading = false
    }
  }
}

api_proxy {
  use_auto_auth_token = true
}

cache {}

listener "tcp" {
  address     = "0.0.0.0:8100"
  tls_disable = true
}

# No vault { address } block: the server address comes from the container's
# BAO_ADDR environment variable. An address set here takes precedence over
# the environment, and "${BAO_ADDR}" is not guaranteed to be expanded in HCL.
