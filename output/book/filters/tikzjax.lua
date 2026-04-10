--[[
tikzjax.lua -- Convert `.tikz` code blocks to <script type="text/tikz"> tags
for browser-side rendering with TikZ.js (drgrice1 fork).

This filter runs BEFORE the pandoc-ext/diagram filter so that diagram.lua
never sees the tikz blocks.
]]

-- Default TikZ libraries used across the book.
-- tikzjax loads these via \usetikzlibrary{...}.
local DEFAULT_LIBS = {
  "angles", "arrows", "arrows.meta", "backgrounds", "bending", "calc",
  "decorations.markings", "decorations.pathmorphing", "fit",
  "intersections", "matrix", "positioning", "quotes", "shapes",
  "shapes.geometric", "shadows.blur",
}

-- Build a set from DEFAULT_LIBS for quick lookup.
local default_lib_set = {}
for _, lib in ipairs(DEFAULT_LIBS) do
  default_lib_set[lib] = true
end

-- Detect TikZ libraries used in the code block.
local function detect_tikz_libs(code)
  local libs = {}
  -- Copy defaults
  for lib, _ in pairs(default_lib_set) do
    libs[lib] = true
  end
  -- Find \usetikzlibrary{...} in the code
  for bracket in code:gmatch("\\usetikzlibrary{([^}]+)}") do
    for item in bracket:gmatch("[^,%s]+") do
      libs[item] = true
    end
  end
  -- Sort for deterministic output
  local sorted = {}
  for lib, _ in pairs(libs) do
    sorted[#sorted + 1] = lib
  end
  table.sort(sorted)
  return table.concat(sorted, ",")
end

-- Build the data-tex-packages JSON string based on what the code needs.
-- tikzjax preloads: tikz, xcolor[svgnames], standalone.
-- We always include amsmath, amssymb, graphicx for safety.
-- pgfplots is added when axis/addplot is detected.
-- pgf-pie is added when \pie is detected.
local function build_tex_packages(code)
  local pkgs = { amsmath = true, amssymb = true, graphicx = true }

  if code:find("\\begin{axis}")
     or code:find("\\begin{polaraxis}")
     or code:find("\\addplot")
     or code:find("\\pgfplotsset") then
    pkgs["pgfplots"] = true
  end

  if code:find("\\pie%[") or code:find("\\pie{") then
    pkgs["pgf-pie"] = true
  end

  -- Collect extra \usepackage from the code (skip tikz, xcolor which are built-in)
  for bracket in code:gmatch("\\usepackage{([^}]+)}") do
    for item in bracket:gmatch("[^,%s]+") do
      if item ~= "tikz" and item ~= "xcolor" then
        pkgs[item] = true
      end
    end
  end

  local parts = {}
  for pkg, _ in pairs(pkgs) do
    parts[#parts + 1] = string.format('"%s":""', pkg)
  end
  table.sort(parts)
  return "{" .. table.concat(parts, ",") .. "}"
end

-- Detect pgfplots sub-libraries (e.g. fillbetween, polar, dateplot).
local function detect_pgfplots_libs(code)
  local libs = {}
  for bracket in code:gmatch("\\usepgfplotslibrary{([^}]+)}") do
    for item in bracket:gmatch("[^,%s]+") do
      libs[#libs + 1] = item
    end
  end
  return libs
end

-- Escape a string for use inside a double-quoted HTML attribute.
local function html_attr_escape(s)
  return s:gsub("&", "&amp;")
          :gsub("<", "&lt;")
          :gsub(">", "&gt;")
          :gsub('"', "&quot;")
end

-- Escape for use inside a JS string literal embedded in an HTML attribute.
local function js_string_escape(s)
  return s:gsub("\\", "\\\\")
          :gsub('"', '\\"')
          :gsub("\n", "\\n")
end

-- Escape only HTML entities in the script body (not the attribute).
local function html_body_escape(s)
  return s:gsub("&", "&amp;")
          :gsub("<", "&lt;")
end

-- Build the data-add-to-preamble content.
-- This puts pgfplotsset, pgfplots libraries, and any user \usepackage
-- into the preamble so they are available when the document starts.
local function build_preamble(code)
  local parts = {}

  -- pgfplots compat
  if code:find("\\begin{axis}")
     or code:find("\\begin{polaraxis}")
     or code:find("\\addplot")
     or code:find("\\pgfplotsset") then
    parts[#parts + 1] = "\\pgfplotsset{compat=1.18}"
  end

  -- pgfplots sub-libraries
  local pgf_libs = detect_pgfplots_libs(code)
  for _, lib in ipairs(pgf_libs) do
    parts[#parts + 1] = string.format("\\usepgfplotslibrary{%s}", lib)
  end

  if #parts == 0 then return nil end
  return table.concat(parts, "\n")
end

return {
  {
    CodeBlock = function(block)
      if not block.classes:includes("tikz") then
        return nil
      end

      local code = block.text

      local tikz_libs = detect_tikz_libs(code)
      local tex_pkgs = build_tex_packages(code)
      local preamble = build_preamble(code)

      -- Build the <script> tag.
      -- The tikzjax JS expects camelCase data attributes:
      --   data-tikz-libraries, data-tex-packages, data-add-to-preamble
      local parts = {}
      parts[#parts + 1] = '<script type="text/tikz"'
      parts[#parts + 1] = string.format(' data-tikz-libraries="%s"', tikz_libs)
      parts[#parts + 1] = string.format(" data-tex-packages='%s'", tex_pkgs)

      if preamble then
        -- Use single quotes for the attribute, double-escape inside
        parts[#parts + 1] = string.format(' data-add-to-preamble="%s"',
                                          html_attr_escape(preamble))
      end

      -- Close the opening tag, add the body, close the script.
      -- The body is the raw TikZ code.  tikzjax reads it as textContent.
      -- We must escape < and & so the HTML parser doesn't choke.
      parts[#parts + 1] = ">\n"
      parts[#parts + 1] = html_body_escape(code)
      parts[#parts + 1] = "\n</script>"

      return pandoc.RawBlock("html", table.concat(parts))
    end,
  },
}
