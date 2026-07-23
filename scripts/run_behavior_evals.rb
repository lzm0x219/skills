#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "fileutils"
require "open3"
require "optparse"
require "pathname"
require "tempfile"
require "tmpdir"
require "timeout"

ROOT = Pathname.new(__dir__).join("..").expand_path
CONTRACT_PATH = ROOT.join("evals", "dsa-design.behavior.json")
SKILL_PATH = ROOT.join("skills", "dsa-design")
EVAL_SKILL_NAME = "dsa-design-working-tree-eval"
DEFAULT_TIMEOUT_SECONDS = Integer(ENV.fetch("CODEX_EVAL_TIMEOUT", "600"))

options = {
  answers: nil,
  case_ids: [],
  codex: ENV.fetch("CODEX_BIN", "codex"),
  list: false,
  model: ENV["CODEX_EVAL_MODEL"],
  show_output: false,
  timeout: DEFAULT_TIMEOUT_SECONDS
}

OptionParser.new do |parser|
  parser.banner = "Usage: ruby scripts/run_behavior_evals.rb [options]"
  parser.on("--list", "List available behavior cases without calling a model") { options[:list] = true }
  parser.on("--case ID", "Run one case; repeat to run several") { |id| options[:case_ids] << id }
  parser.on("--answers DIRECTORY", "Validate saved answers instead of calling Codex") { |path| options[:answers] = path }
  parser.on("--model MODEL", "Override the Codex model") { |model| options[:model] = model }
  parser.on("--codex PATH", "Codex executable or command name") { |path| options[:codex] = path }
  parser.on("--timeout SECONDS", Integer, "Per-case timeout (default: #{DEFAULT_TIMEOUT_SECONDS})") do |seconds|
    options[:timeout] = seconds
  end
  parser.on("--show-output", "Print successful model outputs") { options[:show_output] = true }
end.parse!

contract = JSON.parse(CONTRACT_PATH.read)
cases = contract.fetch("cases")

unless options[:case_ids].empty?
  known_ids = cases.map { |entry| entry.fetch("id") }
  unknown_ids = options[:case_ids] - known_ids
  abort "Unknown case id(s): #{unknown_ids.join(', ')}" unless unknown_ids.empty?
  cases = cases.select { |entry| options[:case_ids].include?(entry.fetch("id")) }
end

if options[:list]
  cases.each do |entry|
    assertions = entry.fetch("expected").fetch("assertions")
    check_count = assertions.values.map(&:length).inject(0, :+)
    puts "#{entry.fetch('id')}\t#{entry.fetch('category')}\t#{check_count} assertion(s)"
  end
  exit 0
end

def command_available?(command)
  return File.executable?(command) if command.include?(File::SEPARATOR)

  ENV.fetch("PATH", "").split(File::PATH_SEPARATOR).any? do |directory|
    File.executable?(File.join(directory, command))
  end
end

def compile_patterns(patterns, label)
  patterns.map do |pattern|
    Regexp.new(pattern, Regexp::IGNORECASE | Regexp::MULTILINE)
  rescue RegexpError => e
    abort "#{label}: invalid regular expression #{pattern.inspect}: #{e.message}"
  end
end

answers_directory = if options[:answers]
                      path = Pathname.new(options[:answers])
                      path.absolute? ? path : ROOT.join(path)
                    end
if answers_directory
  abort "Saved-answer directory not found: #{answers_directory}" unless answers_directory.directory?
else
  abort "Codex executable not found: #{options[:codex]}" unless command_available?(options[:codex])
end
abort "--timeout must be positive" unless options[:timeout].positive?

eval_workspace = nil
unless answers_directory
  eval_workspace = Pathname.new(Dir.mktmpdir("dsa-design-eval-"))
  at_exit do
    FileUtils.remove_entry(eval_workspace) if eval_workspace&.directory?
  end

  eval_skill_path = eval_workspace.join(".agents", "skills", EVAL_SKILL_NAME)
  FileUtils.mkdir_p(eval_skill_path.parent)
  FileUtils.cp_r(SKILL_PATH, eval_skill_path)

  skill_document = eval_skill_path.join("SKILL.md")
  original_document = skill_document.read
  isolated_document = original_document.sub(
    /\A---\nname: dsa-design\n/,
    "---\nname: #{EVAL_SKILL_NAME}\n"
  )
  abort "Unable to isolate working-tree skill frontmatter" if isolated_document == original_document

  skill_document.write(isolated_document)
end

failed = 0

cases.each do |entry|
  case_id = entry.fetch("id")
  expected = entry.fetch("expected")
  assertions = expected.fetch("assertions")
  required_patterns = compile_patterns(assertions.fetch("required_regex"), "#{case_id}.required_regex")
  forbidden_patterns = compile_patterns(assertions.fetch("forbidden_regex"), "#{case_id}.forbidden_regex")
  output_path = nil
  if answers_directory
    answer_path = answers_directory.join("#{case_id}.txt")
    unless answer_path.file?
      warn "[FAIL] #{case_id}: saved answer is missing: #{answer_path}"
      failed += 1
      next
    end
    answer = answer_path.read.strip
  else
    prompt = <<~PROMPT
      Use $#{EVAL_SKILL_NAME} to answer this user request.
      Evaluate only that isolated working-tree skill; do not use an installed skill with a similar name.
      This is a read-only behavior evaluation: do not modify files.
      Return only the concise answer you would give the user.

      User request:
      #{entry.fetch("prompt")}
    PROMPT

    output_file = Tempfile.new(["dsa-design-#{case_id}", ".txt"])
    output_path = output_file.path
    output_file.close

    command = [
      options[:codex],
      "exec",
      "--ephemeral",
      "--ignore-user-config",
      "--sandbox",
      "read-only",
      "--color",
      "never",
      "--cd",
      eval_workspace.to_s,
      "--skip-git-repo-check",
      "--output-last-message",
      output_path
    ]
    command.concat(["--model", options[:model]]) if options[:model] && !options[:model].empty?
    command << "-"

    begin
      stdout, stderr, status = Timeout.timeout(options[:timeout]) do
        Open3.capture3(*command, stdin_data: prompt)
      end
    rescue Timeout::Error
      warn "[FAIL] #{case_id}: timed out after #{options[:timeout]} seconds"
      failed += 1
      next
    end

    unless status.success?
      warn "[FAIL] #{case_id}: Codex exited with status #{status.exitstatus}"
      diagnostics = [stderr, stdout].join("\n").lines.last(20).join
      warn diagnostics unless diagnostics.strip.empty?
      failed += 1
      next
    end

    answer = File.exist?(output_path) ? File.read(output_path).strip : ""
  end

  failures = []
  failures << "answer is empty" if answer.empty?

  required_patterns.each do |pattern|
    failures << "missing required pattern #{pattern.source.inspect}" unless answer.match?(pattern)
  end
  forbidden_patterns.each do |pattern|
    failures << "matched forbidden pattern #{pattern.source.inspect}" if answer.match?(pattern)
  end

  if failures.empty?
    puts "[PASS] #{case_id}"
    puts answer if options[:show_output]
  else
    warn "[FAIL] #{case_id}"
    failures.each { |failure| warn "- #{failure}" }
    warn "--- answer ---"
    warn answer
    failed += 1
  end
ensure
  File.unlink(output_path) if output_path && File.exist?(output_path)
end

if failed.zero?
  puts "PASS: #{cases.length} behavior case(s)."
  exit 0
end

warn "FAIL: #{failed} of #{cases.length} behavior case(s) failed."
exit 1
