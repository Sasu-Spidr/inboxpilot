# Bootstrap configuration packaged for CI-03. CI-05 will add the templates
# that render InboxPilot runtime secrets before this image is deployed.
pid_file = "/tmp/bao-agent.pid"
exit_after_auth = false

auto_auth {
  method "approle" {
    config = {
      role_id_file_path                   = "/etc/inboxpilot/bootstrap/role_id"
      secret_id_file_path                 = "/etc/inboxpilot/bootstrap/secret_id"
      remove_secret_id_file_after_reading = false
    }
  }

  sink "file" {
    config = {
      path = "/tmp/bao-agent-token"
      mode = 0600
    }
  }
}
