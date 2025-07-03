my_global_var = None

def my_func():
    # This setup *should NOT* cause a SyntaxError
    global my_global_var # Global declaration first
    print(my_global_var) # Use after
    my_global_var = 1

my_func()