require_relative 'spc_file.rb'

spc = SpcFile.new('spc_test_files/' + ARGV[0])

puts "========================"
puts ARGV[0]


#puts spc.header

#puts spc.get_dir(0)
#puts spc.get_dir(10)

spc.print_tree

#puts spc.stream_list(66)
#puts spc.read_stream(66, 9608).unpack('d*').to_s
