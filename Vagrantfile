Vagrant::Config.run do |config|
    config.vm.box = "lucid32"
    config.vm.box_url = "http://files.vagrantup.com/lucid32.box"
    config.vm.forward_port 9000, 8080
    config.vm.host_name = "openrural"
    config.vm.network :hostonly, "33.33.33.10"
    config.vm.customize ["modifyvm", :id, "--memory", 1536]
    config.vm.share_folder("v-root", "/vagrant", ".", :nfs => true)
end
