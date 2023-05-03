
class test:
    a = 0
    
toto = test()


menu_navigation_map = {
    "cv/gate/mod" : 
        {"module A" : {            
            "data_pointer" : toto,
            "gate level" : {
                "values" : ["low", "high"]
                },
            "cv max" : {
                "values" : ["5V", "10V"]
            },
        },
         "module B" : {},
         "module C" : {},
         "module D" : {}
         }
    
    
}
