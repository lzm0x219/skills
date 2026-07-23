#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "pathname"
require "uri"
require "yaml"

ROOT = Pathname.new(__dir__).join("..").expand_path
LICENSE_PATH = ROOT.join("LICENSE")
SKILLS_DIR = ROOT.join("skills")
EVAL_CONTRACT = ROOT.join("evals", "dsa-design.behavior.json")
BEHAVIOR_RUNNER = ROOT.join("scripts", "run_behavior_evals.rb")
BEHAVIOR_FIXTURE_DIR = ROOT.join("evals", "fixtures", "dsa-design")
SKILL_NAME_PATTERN = /\A[a-z0-9]+(?:-[a-z0-9]+)*\z/
ALLOWED_FRONTMATTER_KEYS = %w[name description].freeze
MARKDOWN_LINK_PATTERN =
  /!?\[[^\]]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+(?:"[^"]*"|'[^']*'|\([^)]*\)))?\s*\)/
REQUIRED_EVAL_CASES = %w[
  prose-edit-no-trigger
  simple-crud-no-forced-dsa
  top-k-material-decision
  delegated-choice-no-pause
].freeze

errors = []
skill_count = 0
markdown_count = 0
local_link_count = 0

unless LICENSE_PATH.file?
  errors << "LICENSE: file is missing"
else
  license_text = LICENSE_PATH.read
  required_license_markers = [
    "Apache License",
    "Version 2.0, January 2004",
    "END OF TERMS AND CONDITIONS"
  ]
  missing_license_markers = required_license_markers.reject { |marker| license_text.include?(marker) }
  unless missing_license_markers.empty?
    errors << "LICENSE: missing Apache-2.0 markers: #{missing_license_markers.join(', ')}"
  end
end

def load_yaml(path, errors, label)
  parsed = YAML.safe_load(
    path.read,
    permitted_classes: [],
    permitted_symbols: [],
    aliases: false
  )
  unless parsed.is_a?(Hash)
    errors << "#{label}: expected a YAML mapping"
    return nil
  end
  parsed
rescue Psych::Exception => e
  errors << "#{label}: invalid YAML (#{e.message.lines.first.strip})"
  nil
rescue Errno::ENOENT
  errors << "#{label}: file is missing"
  nil
end

def frontmatter_for(path, errors)
  lines = path.readlines
  unless lines.first&.strip == "---"
    errors << "#{path.relative_path_from(ROOT)}: missing opening YAML frontmatter delimiter"
    return nil
  end

  closing_index = lines.each_index.drop(1).find { |index| lines[index].strip == "---" }
  unless closing_index
    errors << "#{path.relative_path_from(ROOT)}: missing closing YAML frontmatter delimiter"
    return nil
  end

  yaml = YAML.safe_load(
    lines[1...closing_index].join,
    permitted_classes: [],
    permitted_symbols: [],
    aliases: false
  )
  unless yaml.is_a?(Hash)
    errors << "#{path.relative_path_from(ROOT)}: frontmatter must be a YAML mapping"
    return nil
  end
  yaml
rescue Psych::Exception => e
  errors << "#{path.relative_path_from(ROOT)}: invalid frontmatter YAML (#{e.message.lines.first.strip})"
  nil
end

def local_markdown_targets(path)
  targets = []
  fence_character = nil
  fence_length = 0

  path.each_line.with_index(1) do |line, line_number|
    if fence_character
      if line.match?(/^\s*#{Regexp.escape(fence_character)}{#{fence_length},}/)
        fence_character = nil
        fence_length = 0
      end
      next
    end

    fence = line.match(/^\s*(`{3,}|~{3,})/)
    if fence
      fence_character = fence[1][0]
      fence_length = fence[1].length
      next
    end

    line.scan(MARKDOWN_LINK_PATTERN) do |match|
      raw_target = match.first
      raw_target = raw_target[1...-1] if raw_target.start_with?("<") && raw_target.end_with?(">")
      next if raw_target.empty? || raw_target.start_with?("#", "//")
      next if raw_target.match?(/\A[a-z][a-z0-9+.-]*:/i)

      path_part = raw_target.split(/[?#]/, 2).first
      next if path_part.nil? || path_part.empty?

      begin
        targets << [URI::DEFAULT_PARSER.unescape(path_part), line_number]
      rescue URI::InvalidURIError
        targets << [path_part, line_number]
      end
    end
  end

  targets
end

skill_dirs = SKILLS_DIR.directory? ? SKILLS_DIR.children.select(&:directory?).sort : []
errors << "skills/: directory is missing or contains no skill directories" if skill_dirs.empty?
skill_dirs.each do |skill_dir|
  errors << "#{skill_dir.relative_path_from(ROOT)}: missing SKILL.md" unless skill_dir.join("SKILL.md").file?
end
skill_files = skill_dirs.map { |skill_dir| skill_dir.join("SKILL.md") }.select(&:file?)

skill_files.each do |skill_file|
  skill_count += 1
  skill_dir = skill_file.dirname
  directory_name = skill_dir.basename.to_s
  relative_skill_file = skill_file.relative_path_from(ROOT)
  metadata = frontmatter_for(skill_file, errors)

  if metadata
    name = metadata["name"]
    description = metadata["description"]
    unexpected_keys = metadata.keys - ALLOWED_FRONTMATTER_KEYS

    unless unexpected_keys.empty?
      errors << "#{relative_skill_file}: unexpected frontmatter keys: #{unexpected_keys.sort.join(', ')}"
    end

    unless name.is_a?(String) && name.match?(SKILL_NAME_PATTERN) && name.length <= 64
      errors << "#{relative_skill_file}: name must be a lowercase hyphen-case string of at most 64 characters"
    end
    if name.is_a?(String) && name != directory_name
      errors << "#{relative_skill_file}: name #{name.inspect} does not match directory #{directory_name.inspect}"
    end
    unless description.is_a?(String) && !description.strip.empty? &&
           description.length <= 1024 && !description.match?(/[<>]/)
      errors << "#{relative_skill_file}: description must be a non-empty string of at most 1024 characters without angle brackets"
    end
  end

  openai_path = skill_dir.join("agents", "openai.yaml")
  openai = load_yaml(openai_path, errors, openai_path.relative_path_from(ROOT).to_s)
  if openai
    interface = openai["interface"]
    unless interface.is_a?(Hash)
      errors << "#{openai_path.relative_path_from(ROOT)}: interface must be a mapping"
      interface = {}
    end

    %w[display_name short_description default_prompt].each do |field|
      value = interface[field]
      unless value.is_a?(String) && !value.strip.empty?
        errors << "#{openai_path.relative_path_from(ROOT)}: interface.#{field} must be a non-empty string"
      end
    end

    short_description = interface["short_description"]
    if short_description.is_a?(String) && !(25..64).cover?(short_description.length)
      errors << "#{openai_path.relative_path_from(ROOT)}: interface.short_description must contain 25-64 characters"
    end

    default_prompt = interface["default_prompt"]
    if default_prompt.is_a?(String) && !default_prompt.include?("$#{directory_name}")
      errors << "#{openai_path.relative_path_from(ROOT)}: interface.default_prompt must mention $#{directory_name}"
    end

    policy = openai["policy"]
    unless policy.is_a?(Hash)
      errors << "#{openai_path.relative_path_from(ROOT)}: policy must be a mapping"
      policy = {}
    end
    implicit = policy["allow_implicit_invocation"]
    unless implicit == true || implicit == false
      errors << "#{openai_path.relative_path_from(ROOT)}: policy.allow_implicit_invocation must be a boolean"
    end
  end
end

markdown_files = [ROOT.join("README.md"), *SKILLS_DIR.glob("**/*.md")]
markdown_files.select(&:file?).uniq.sort.each do |markdown_file|
  markdown_count += 1
  local_markdown_targets(markdown_file).each do |target, line_number|
    local_link_count += 1
    resolved = markdown_file.dirname.join(target).expand_path
    relative_source = markdown_file.relative_path_from(ROOT)
    within_repo = resolved == ROOT || resolved.to_s.start_with?("#{ROOT}#{File::SEPARATOR}")

    unless within_repo
      errors << "#{relative_source}:#{line_number}: local link escapes the repository: #{target}"
      next
    end
    errors << "#{relative_source}:#{line_number}: missing local link target: #{target}" unless resolved.exist?
  end
end

begin
  contract = JSON.parse(EVAL_CONTRACT.read)
  unless contract.is_a?(Hash)
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: expected a JSON object"
    contract = {}
  end

  unless contract["automated"] == true
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: automated must be true"
  end
  unless contract["schema_version"] == 1
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: schema_version must be 1"
  end
  unless contract["skill"] == "dsa-design"
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: skill must be \"dsa-design\""
  end

  execution = contract["execution"]
  unless execution.is_a?(Hash) && execution["mode"] == "codex-cli"
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: execution.mode must be \"codex-cli\""
  end
  unless execution.is_a?(Hash) && execution["runner"] == BEHAVIOR_RUNNER.relative_path_from(ROOT).to_s
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: execution.runner must reference the repository behavior runner"
  end
  errors << "#{BEHAVIOR_RUNNER.relative_path_from(ROOT)}: file is missing" unless BEHAVIOR_RUNNER.file?

  cases = contract["cases"]
  unless cases.is_a?(Array)
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: cases must be an array"
    cases = []
  end

  case_ids = cases.each_with_object([]) do |entry, ids|
    ids << entry["id"] if entry.is_a?(Hash) && entry["id"]
  end
  case_id_counts = case_ids.each_with_object(Hash.new(0)) { |id, counts| counts[id] += 1 }
  duplicate_case_ids = case_id_counts.select { |_id, count| count > 1 }.keys
  unless duplicate_case_ids.empty?
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: duplicate case ids: #{duplicate_case_ids.join(', ')}"
  end
  missing_cases = REQUIRED_EVAL_CASES - case_ids
  unless missing_cases.empty?
    errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: missing required cases: #{missing_cases.join(', ')}"
  end

  cases.each_with_index do |entry, index|
    label = "#{EVAL_CONTRACT.relative_path_from(ROOT)}: cases[#{index}]"
    unless entry.is_a?(Hash)
      errors << "#{label} must be an object"
      next
    end

    errors << "#{label}.id must be a non-empty string" unless entry["id"].is_a?(String) && !entry["id"].empty?
    errors << "#{label}.prompt must be a non-empty string" unless entry["prompt"].is_a?(String) && !entry["prompt"].strip.empty?
    if entry["id"].is_a?(String) && !entry["id"].empty?
      fixture_path = BEHAVIOR_FIXTURE_DIR.join("#{entry['id']}.txt")
      unless fixture_path.file? && !fixture_path.read.strip.empty?
        errors << "#{fixture_path.relative_path_from(ROOT)}: saved answer must exist and be non-empty"
      end
    end

    expected = entry["expected"]
    unless expected.is_a?(Hash)
      errors << "#{label}.expected must be an object"
      next
    end
    %w[trigger_skill pause_for_user_choice].each do |field|
      value = expected[field]
      unless value == true || value == false
        errors << "#{label}.expected.#{field} must be a boolean"
      end
    end
    %w[must must_not].each do |field|
      value = expected[field]
      unless value.is_a?(Array) && !value.empty? &&
             value.all? { |item| item.is_a?(String) && !item.strip.empty? }
        errors << "#{label}.expected.#{field} must be an array of non-empty strings"
      end
    end

    assertions = expected["assertions"]
    unless assertions.is_a?(Hash)
      errors << "#{label}.expected.assertions must be an object"
      next
    end
    %w[required_regex forbidden_regex].each do |field|
      patterns = assertions[field]
      unless patterns.is_a?(Array) && !patterns.empty? &&
             patterns.all? { |pattern| pattern.is_a?(String) && !pattern.empty? }
        errors << "#{label}.expected.assertions.#{field} must be an array of non-empty regular expressions"
        next
      end
      patterns.each do |pattern|
        Regexp.new(pattern)
      rescue RegexpError => e
        errors << "#{label}.expected.assertions.#{field}: invalid regular expression #{pattern.inspect} (#{e.message})"
      end
    end
  end
rescue JSON::ParserError => e
  errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: invalid JSON (#{e.message.lines.first.strip})"
rescue Errno::ENOENT
  errors << "#{EVAL_CONTRACT.relative_path_from(ROOT)}: file is missing"
end

if errors.empty?
  puts "PASS: validated #{skill_count} skill(s), #{markdown_count} Markdown file(s), " \
       "#{local_link_count} local link(s), and the dsa-design behavior contract."
  exit 0
end

warn "FAIL: found #{errors.length} validation error(s):"
errors.each { |error| warn "- #{error}" }
exit 1
