my_global_var = None

def my_func():
    # This setup *should* cause a SyntaxError if Python behaves as expected
    print(my_global_var) # First use
    global my_global_var # Global declaration after use
    my_global_var = 1

my_func()