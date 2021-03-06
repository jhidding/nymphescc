local system = require 'pandoc.system'

local make_preamble = [[
.RECIPEPREFIX := $(.RECIPEPREFIX) 

target_dir := %s
target := $(target_dir)/%s
]]

function CodeBlock(block)
    if block.classes[1] == "make" then
        local caption, rawsrc = block.text:match("(.-)\n%-%-%-\n(.*)")
        if not caption then
            rawsrc = block.text
            caption = ""
        end
        outfile = block.attributes["target"]
        target_dir = block.attributes["dir"] or "docs"
        system.with_temporary_directory("run-make", function (tmpdir)
            local src = make_preamble:format(target_dir, outfile) .. rawsrc
            local f = io.open(tmpdir .. "/Makefile", "w")
            f:write(src)
            f:close()
            os.execute("mkdir -p " .. target_dir .. "/$(dirname " .. outfile ..")")
            os.execute("make -f " .. tmpdir .. "/Makefile " .. target_dir .. "/" .. outfile)
        end)
        return pandoc.Para({pandoc.Image({pandoc.Str(caption)}, outfile, caption, {class = "figure"})})
    end
end

