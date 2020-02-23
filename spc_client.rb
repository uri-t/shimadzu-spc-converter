require_relative 'spc_file.rb'

spc = SpcFile.new(ARGV[0])

puts "========================"
puts ARGV[0]

puts spc.header
puts spc.sat_sids.to_s

#puts spc.get_dir(804)
#spc.print_tree
#nodes = spc.all_nodes
#root_node = spc.get_dir(1)


#puts spc.search_sibs(root_node, "DataStorageHeaderInfo")

puts spc.read_stream(10222, 400008).unpack('d*')

#nodes.select{|x| x[:name] == "PageTexts0"}.each do |node|
#  puts spc.read_stream(node[:sid], node[:size]).select{|x| x!= "\x00"}.join
#end

