import math as m
import random as r 

def pHit(CEP,  rBlast, length, width): 
    '''
    function for finding probability of hit given circular error probable, 
    lethal blast radius, and length and width of rectangular target
    '''

    sigma = CEP/1.1774 # convert CEP to 1 standard deviation

    # Find the x and y coordinates for rectangle that is target area + blast radius
    # The retangular area is defined to be (-a,-b) & (a,b) as bottom left and top right points
    a = length/2 + rBlast
    b = width/2 + rBlast
    # Solves the normal distribution 
    pHit = m.sqrt( (1- m.exp((-2*a**2)/(m.pi*sigma**2))) * (1- m.exp((-2*b**2)/(m.pi*sigma**2))))

    return pHit


#print(pHit(10, 1, 10, 10))
