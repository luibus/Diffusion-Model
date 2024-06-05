# -*- coding: utf-8 -*-
"""prueba_de_tiempos_cuda__evol_pesos.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/110hJBNSp8D67EMMq1yQjH-OVxWp0K3LR

implementación de la espiral. Aquí buscamos crear una difusión de una serie de datos en coordenadas.

Llamada a las librerias
"""

# el objetivo es crear un proceso de difusion para datos 2D
import numpy as np
import torch
import torch.nn as nn
from matplotlib import pyplot as plt
from torch.optim import Adam
#from torch import optim

DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(DEVICE)
#a.to(DEVICE)

"""El tensor con el que trabajaremos es data_bien ahora crearemos la clase difusión"""

class Difusion:
    def __init__(self,data,W,paso_temp):
        self.n=data.size(dim=0) #numero de puntos que se quiere samplear
        self.m=data.size(dim=1)
        self.T = paso_temp   #pasos de tiempo
        self.diffusion_rate = 0.01   #para la difusión normal
        self.mu=0
        self.var=0.1
        self.data=data
        self.data2=data
        self.start=1e-4
        self.end=0.02
        self.betas = self.linear_beta_schedule() #llamada interior
        self.alphas = 1. - self.betas
        self.alphas_cumprod = torch.from_numpy(np.cumprod(self.alphas, axis=0))
        self.alpha_hat=self.alphas_cumprod
    # Beta no lineal
    def linear_beta_schedule(self):
        return np.linspace(self.start, self.end, self.T)

    # Funcion para aplicar el modelo de difusion hacia adelante
    # Es el paso del forward step con el reparametrization trick
    def forward_diffusion(self):
        ruido=torch.normal(self.mu * torch.ones(self.n),self.var)
        #ruido=0.1*ruido
        for t in range(self.T):

            self.data =(np.sqrt(1-self.diffusion_rate)*self.data) + (np.sqrt(self.diffusion_rate)*ruido)

        return self.data,ruido

    def forward_diffusion_all(self):
        all_data = np.zeros((self.T+1,self.data.shape[0],self.data.shape[1]))
        all_data[0,:] = self.data[:]
        for t in range(self.T):

            self.data =(np.sqrt(1-self.diffusion_rate)*self.data) + (np.sqrt(self.diffusion_rate)*torch.normal(self.mu * torch.ones(2,self.n),self.var))
            all_data[t+1,:] = self.data[:]

        return all_data

    # Paso forward con alphas acumulativas
    def forward_alpha(self):
        ruido=torch.normal(self.mu * torch.ones(self.m,self.n),self.var)#de cara a la nueva distribucion de data pongo 1 en vez de 2
        #ruido=(1/(1+torch.exp(-(ruido))))
        # ruido=0.1*ruido
        data2 =np.sqrt(self.alphas_cumprod[self.T-1])*self.data2.T + (np.sqrt(1-self.alphas_cumprod[self.T-1])*ruido)
        return data2,ruido
    

    #proceso forward que se empleará para entrenar tiempo a tiempo cada máquina al completo
    def forward_alpha_last_update(self,Time):
        ruido=torch.normal(self.mu * torch.ones(self.m,self.n),self.var)#de cara a la nueva distribucion de data pongo 1 en vez de 2
        #ruido=(1/(1+torch.exp(-(ruido))))
        # ruido=0.1*ruido
        data2 =np.sqrt(self.alphas_cumprod[Time-1])*self.data2.T + (np.sqrt(1-self.alphas_cumprod[Time-1])*ruido)
        return data2,ruido
    def reverse_sampling(self, W,ruido,model_dict):
            with torch.no_grad():
                x=torch.normal(self.mu * torch.ones(self.n),self.var).to(DEVICE) #sampling de una distribución normal
                #x[(x.size(dim=0)-1)]=T #ponemos el último valor como el paso de tiempo correspondiente
                #x=torch.transpose(x,0,1)
                #print(x.size())
                #x=(1/(1+torch.exp(-(x))))
                #x=0.1*x#lo que cambiamos para ir o no a los datos
                #x=ruido #al comentar esta linea lo hacemos tomar un ruido base aleatorio si no usa la muestra característica
                #predicted_noise=W
                predicted_noise=torch.ones(self.n).to(DEVICE)
                #for i in range(x.size(dim=0)):
                #    predicted_noise[i]=torch.tensor(1/(1+torch.exp(-(torch.dot(W[i,:],x[:])))))-0.5                 #OJO AL CAMBIO  la matriz de pesos es ahora pixeles en las distintas filas y pesos de entrada en las distintas columnas
                #                #print(predicted_noise)
                                #print(i)
                #print(W[1,2,:].size())
                #print(x[:].size())
                
                for i in reversed(range(self.T)):
                        alpha = self.alphas[i] #los alpha y alpha coump de el paso específico de la trayectoria reverse
                        alpha_hat = self.alphas_cumprod[i]
                        beta = self.betas[i]

                        
                        model=model_dict[str(i)]
                        model.eval()
                        predicted_noise=model(x)
                        

                        #for j in range(x.size(dim=0)-1):
                        #    predicted_noise[j]=2*(torch.tensor(1/(1+torch.exp(-(torch.dot(W[i,j,:],x[:])))))-0.5)
                            #print(predicted_noise)
                            #print(i)
                        if i > 1:
                            noise= torch.normal(self.mu * torch.ones(self.n),self.var).to(DEVICE)
                            #noise=noise*0.1
                            #noise = torch.zeros_like(x)
                            #noise = torch.randn_like(x) #aquí generamos el ruido antes de llamar a las clases asi que no haria falta generarlo despues, solo usar noise, o bien usar ruido_util solo que todavia no lo habremos llamado
                        else:
                            noise = torch.zeros(self.n).to(DEVICE)
                        x = 1 / np.sqrt(alpha) * (x - ((1 - alpha) / (torch.sqrt(1 - alpha_hat))) * predicted_noise) + np.sqrt(beta) * noise
                        #x[(x.size(dim=0)-1)]=i+1 #aqui igualamos el termino del tiempo al paso por el que vamos
                        model.train()
                    #no deberia ser alpha_hat?
            
#el reverse personalizable
                        
    def reverse_sampling_last_update(self, W,ruido,model_dict,Time):
            with torch.no_grad():
                x=torch.normal(self.mu * torch.ones(self.n),self.var).to(DEVICE) #sampling de una distribución normal
                #x[(x.size(dim=0)-1)]=T #ponemos el último valor como el paso de tiempo correspondiente
                #x=torch.transpose(x,0,1)
                #print(x.size())
                #x=(1/(1+torch.exp(-(x))))
                #x=0.1*x#lo que cambiamos para ir o no a los datos
                #x=ruido #al comentar esta linea lo hacemos tomar un ruido base aleatorio si no usa la muestra característica
                #predicted_noise=W
                predicted_noise=torch.ones(self.n).to(DEVICE)
                #for i in range(x.size(dim=0)):
                #    predicted_noise[i]=torch.tensor(1/(1+torch.exp(-(torch.dot(W[i,:],x[:])))))-0.5                 #OJO AL CAMBIO  la matriz de pesos es ahora pixeles en las distintas filas y pesos de entrada en las distintas columnas
                #                #print(predicted_noise)
                                #print(i)
                #print(W[1,2,:].size())
                #print(x[:].size())
                
                for i in reversed(range(Time)):
                        alpha = self.alphas[i] #los alpha y alpha coump de el paso específico de la trayectoria reverse
                        alpha_hat = self.alphas_cumprod[i]
                        beta = self.betas[i]

                        
                        model_aux=model_dict[str(i)]
                        #model.eval()
                        predicted_noise=model_aux(x)
                        

                        #for j in range(x.size(dim=0)-1):
                        #    predicted_noise[j]=2*(torch.tensor(1/(1+torch.exp(-(torch.dot(W[i,j,:],x[:])))))-0.5)
                            #print(predicted_noise)
                            #print(i)
                        if i > 1:
                            noise= torch.normal(self.mu * torch.ones(self.n),self.var).to(DEVICE)
                            #noise=noise*0.1
                            #noise = torch.zeros_like(x)
                            #noise = torch.randn_like(x) #aquí generamos el ruido antes de llamar a las clases asi que no haria falta generarlo despues, solo usar noise, o bien usar ruido_util solo que todavia no lo habremos llamado
                        else:
                            noise = torch.zeros(self.n).to(DEVICE)
                        x = 1 / np.sqrt(alpha) * (x - ((1 - alpha) / (torch.sqrt(1 - alpha_hat))) * predicted_noise) + np.sqrt(beta) * noise
                        #x[(x.size(dim=0)-1)]=i+1 #aqui igualamos el termino del tiempo al paso por el que vamos
                        #model.train()
                    #no deberia ser alpha_hat?
            

            return x

"""Llamo a la clase

ENTRENAMIENTO
"""

def read_data(images_file, labels_file):
    x = np.loadtxt(images_file, delimiter=',')
    y = np.loadtxt(labels_file, delimiter=',')
    return x, y

train_data, train_labels = read_data('./images_train.csv', './labels_train.csv')
test_data, test_labels = read_data('./images_test.csv', './labels_test.csv')

x=torch.from_numpy(train_data).float()
data_bien=x
test_bien=torch.from_numpy(test_data).float()
print(data_bien.size())#num muestras,dim x
data_bien=(torch.transpose(data_bien,0,1)/255)-0.5#normalizado               HE QUITADO LA NORMALIZACIÓN
test_bien=(torch.transpose(test_bien,0,1)/255)-0.5
for i in range(data_bien.size(dim=1)):
    data_bien[:,i]=(data_bien[:,i]-torch.mean(data_bien[:,i]))/torch.std(data_bien[:,i]) #centrando la data en la media
for i in range(test_bien.size(dim=1)):    
    test_bien[:,i]=(test_bien[:,i]-torch.mean(test_bien[:,i]))/torch.std(test_bien[:,i]) #centrando la data en la media

T=1000
#W=torch.rand([T,data_bien.size(dim=0),data_bien.size(dim=0)])/4    #OJO a donde ponemos el +1
#print(W.size())#iniciamos nuestra matriz de pesos que va a tener los pesos suficientes para cada salida para cada entrada por eso las 3 dimensiones

#prueba=torch.normal(0* torch.ones(16000),1)
#print(prueba.size())

"""Reducción de la data"""

data_bien = data_bien[:,np.where(train_labels==1)[0]]
test_bien = test_bien[:,np.where(test_labels==1)[0]]
print(data_bien.size())
print(test_bien.size())
data_bien=data_bien[:,:900]
test_bien=test_bien[:,:900]
print(data_bien.size())


#TIEMPO
ruido=torch.ones(T,data_bien.size(dim=1),data_bien.size(dim=0))
X=torch.ones(T,data_bien.size(dim=1),data_bien.size(dim=0))


for j in range(1,T+1): #j entra como el tiempo pero habra que restarle uno para usarlo como indice
    print('vamos por: ',j)
    # for i in range(data_bien.size(dim=1)):
        #print('vamos por: ',i)
    user1=Difusion(torch.clone(data_bien),None,j)
        #forward_result ,ruido_util_itera= user1.forward_diffusion()
    forward_alpha_result, ruido_util = user1.forward_alpha()
        #print(forward_result.size())
    X[j-1,:,:data_bien.size(dim=0)]=forward_alpha_result[:]
    #X[j-1,:,data_bien.size(dim=0)]=j
    ruido[j-1,:,:data_bien.size(dim=0)]=ruido_util[:]
    #ruido[j-1,:,data_bien.size(dim=0)]=j

#ahora X y ruido me almacenan los distintos pasos de tiempo en los distintos j con los distintos ruidos a cada paso de tiempo PERO para luego el reverse al ser forward alpha no cuadra muy bien¿?
print(ruido.size())
print(X.size())
ruido=torch.reshape(ruido,[T,data_bien.size(dim=1),data_bien.size(dim=0)])
X=torch.reshape(X,[T,data_bien.size(dim=1),data_bien.size(dim=0)])
print(ruido.size())
print(X.size())
#print(X)
Y=ruido
permut=torch.randperm(X.size(0))
print(permut.size())
x_preshuffle=X
#X=X[permut,:,:] #al estar comentado no estamos mezclando los samples
#Y=Y[permut,:,:]


    #

"""Visualizando una muestra cualquiera se le puede poner aumentando T mayor difusión

"""

plt.imshow(np.transpose(data_bien[:784,1].reshape(28,28)))

#import matplotlib.pyplot as plt
plt.imshow(np.transpose(X[j-1,1,:784].reshape(28,28)))

#import matplotlib.pyplot as plt
plt.imshow(np.transpose(ruido[j-1,1,:784].reshape(28,28)))

#print(X[:784,1])#cerca de 1 pero no normalizado

#print(ruido[:784,1])#cerca de 1 pero no normalizado

"""EL GRAN RESHAPE"""

#NO puedo por culpa del batch posria hacerlo despes de tomar el batch
#ruido=torch.reshape(ruido,[data_bien.size(dim=0),data_bien.size(dim=1)*T])r
#X=torch.reshape(X,[data_bien.size(dim=0),data_bien.size(dim=1)*T])
#W=torch.reshape(W,[data_bien.size(dim=0),data_bien.size(dim=1)*T])

"""Ahora comprobamos que nuestra matriz de ruido tiene valores entre -0.5 y 0.5 para que la sigmoid que estamos usand pueda barrerla"""

#print(torch.max(ruido[:784,1,T-1]-(X[:784,1,T-1])))#son muy parecidos mucha disfusión? Sí a menor paso de t mejor por eso hay que entrenar t como parámetro
print(torch.max(ruido))
print(torch.max(X))
#print(torch.min(ruido[:784,1,T-1]-(X[:784,1,T-1])))#son muy parecidos mucha disfusión? Sí a menor paso de t mejor por eso hay que entrenar t como parámetro
print(torch.min(ruido))
print(torch.min(X))

"""Modelo multicapa

"""

#T=300
#D_in, H, D_out = 785, 800, 784 #784 entradas, 100 neuronas en la capa oculta y 784 salidas.
#model=torch.nn.ParameterList([torch.nn.Sequential(
#    torch.nn.Linear(D_in, H),
#    torch.nn.ReLU(),
#    torch.nn.Linear(H, D_out),
#    )])
#for i in range(T-1):
#    model.append([torch.nn.Sequential( #PUEDE que haya que meter la otra variable que enumere el paso de tiempo en que nos encontramos ya que no podemos vectorizar el modelo
#    torch.nn.Linear(D_in, H),
#    torch.nn.ReLU(),
#    torch.nn.Linear(H, D_out),
#    )])


errores = 10

learning_rate = 0.0001 #empezar en 0.1 en bajas distancias el mejor 0,0001 con un coseno se podria tener un buen learning rate
almac_er=torch.ones(10)
tol_pass=1#mide el que la actualizacion del error se mantenga alta o cambia el learning
almac=0
cambio=0
cont_aux=1
cont_aux_continuo=0 #va a ser el que vaya dando entradas a array_images
frame_num= 300 #cantidad de toma de datos totales
train_gap=1 #variable del numero de frames entre toma de datos
array_images=torch.ones(frame_num,784)
batch=10


salida_ploteable=torch.ones(3,frame_num*train_gap)
salida_ploteable_test=torch.ones(3,frame_num*train_gap)
for t in range(int(T/50)):

    for m in range(3):
        D_in, H, D_out = 784, 200+m*100, 784 #784 entradas, 100 neuronas en la capa oculta y 784 salidas.
        model_dict=torch.nn.ParameterDict()
        #loss_dict=torch.nn.ParameterDict()
        for i in {str(t)}: #for sub in range(T-301,T-300)}:
            model_dict[i] = torch.nn.Sequential( #PUEDE que haya que meter la otra variable que enumere el paso de tiempo en que nos encontramos ya que no podemos vectorizar el modelo
            torch.nn.Linear(D_in, H),
            torch.nn.ReLU(),
            torch.nn.Linear(H, D_out),
            )
        #print(model)
        #la llamada del modelo tendrá que ser del tipo
        #b=model_dict["3"]
        #outputs = b(-torch.randn(64, 2,784).to(DEVICE))
        #outputs = model(X)
        #print(model_dict.size)
        #ara mandarlo a GPU
        #model_dict.to(DEVICE)
        #print(model_dict.parameters())




        #aux_1_X=torch.ones(T,data_bien.size(dim=0)+1,data_bien.size(dim=1))
        #aux_2_W=torch.ones(T,data_bien.size(dim=0),data_bien.size(dim=1)+1)
        #aux_1_X[:,:data_bien.size(dim=0),:]=X
        #aux_2_W[:,:,:data_bien.size(dim=0)]=W
        #X=X.to(DEVICE)
        #ruido=ruido.to(DEVICE)
        #Y=Y.to(DEVICE)
        #print(W.size())
        #print(aux_1_X[T-1,:,1].size())
        user1=Difusion(torch.clone(data_bien),None,T)
        user2=Difusion(torch.clone(test_bien),None,T)
        l=[]
        x_util=X[0,:,:]
        x_test=X[0,:,:]
        y_util=Y[0,:,:]
        y_test=Y[0,:,:]
        enumerador=0
        loss_c=(nn.MSELoss(reduction='mean'))#/batch
        #model_dict.train()
        for i in {str(t)}:# for sub in range(T-301,T-300)}

            epoch = 1
            cont_aux=1
            cont_aux_continuo=0
            torch.cuda.empty_cache
            model=model_dict[i]
            model=model.to(DEVICE)
            optimizer = Adam(model.parameters(),lr=learning_rate)
            model.train()
            cont=0
            while errores>0 and epoch<=frame_num*train_gap:
                
                error_dis=0
                #for i in {str(sub) for sub in range(T)}: 
                #model=model_dict[i].to(DEVICE)
                
                
                l=[]
                l_test=[]
                #for j in range(int(X.size(dim=1)/batch)):
                #tenemos un diccionario de modelos para cada tiempo T al que vamos a ir llamando y entrenando por separado vectorial? STLM?                                                          #DEFINO BATCH
                    
                    #al mezclar entrenmiento y evaluacion con torch no grad se puede meter? si no quitar torch no grad
                    #for i in {str(sub) for sub in range(T)}:
                    #  model=model_dict[i].to(DEVICE)
                    #  next_prediction = model(X[int(i),range((j*batch),((j*batch)+batch)),:]) #next prediction es vectorial de tamaño 1600      [:,l+j*batch]    de esta forma va a ser
                    #  loss_dict[i]=next_prediction
                    #print(next_prediction)
                    #loss=-next_prediction+Y[:,range((j*batch),((j*batch)+batch)),:]
                    #loss=abs(loss).mean()
                    #loss=torch.square(loss)
                    #print(loss)
                #for i in {str(sub) for sub in range(T)}:
                forward_alpha_result, ruido_util = user1.forward_alpha_last_update(int(i)+1)
                forward_alpha_result_test, ruido_util_test = user2.forward_alpha_last_update(int(i)+1)
                #print(forward_result.size())
                x_util[:,:data_bien.size(dim=0)]=forward_alpha_result[:]
                x_test[:,:data_bien.size(dim=0)]=forward_alpha_result_test[:] #aqui metemos los tests
                x_util=x_util.cpu()
                x_test=x_test.cpu()
                #X[j-1,:,data_bien.size(dim=0)]=j
                y_util[:,:data_bien.size(dim=0)]=ruido_util[:]
                y_test[:,:data_bien.size(dim=0)]=ruido_util_test[:]
                y_util=y_util.cpu()  
                y_test=y_test.cpu()  
                permut=torch.randperm(x_util.size(0))                             #NUEVO
                #print(permut.size())
                #x_preshuffle=X
                x_util=x_util[permut,:] #al estar comentado no estamos mezclando los samples
                x_test=x_test[permut,:]
                y_util=y_util[permut,:]
                y_test=y_test[permut,:]
                    #out=model(X[int(i),:,:])
                for j in range(int(X.size(dim=1)/batch)):
                    #model=model_dict[i].to(DEVICE)
                    a=x_util[range((j*batch),((j*batch)+batch)),:].to(DEVICE) 
                    b=y_util[range((j*batch),((j*batch)+batch)),:].to(DEVICE) 
                    loss=loss_c(model(a),b)
                    a=x_test[range((j*batch),((j*batch)+batch)),:].to(DEVICE) 
                    b=y_test[range((j*batch),((j*batch)+batch)),:].to(DEVICE) 
                    loss_test=loss_c(model(a),b)
                    
                    optimizer.zero_grad() #igual con el batch que ponemos no nos interesa poner a cero los parámetros hasta que no acabe el batch entero?
                    #print(loss_dict.items().size())
                    l.append(loss)
                    l_test.append(loss_test) #cremos una l con samples a las que no les aplicamos el modelo
                    loss.backward()
                    optimizer.step()
                        #model_dict[i]=model
                    #with torch.no_grad():
                    #    for param in model.parameters():
                    #        param -= learning_rate*param.grad
                    #model_dict[i]=model

                #print(loss)

                #[W,error_dis] = update_state(W.to(DEVICE), learning_rate, X.to(DEVICE).float(), Y.to(DEVICE),error_dis)#he cambiado un uno en la Y por i
                    #print(i)
                

                #va tomando muetras de cada paso que vamos añadiendo
                model_dict[i]=model
                #if cont_aux==train_gap:
                #   samplenum=1
                #  print(cont_aux_continuo)
                # salida_sampled = user1.reverse_sampling_last_update(None,X[T-1,samplenum,:].to(DEVICE),model_dict.to(DEVICE),int(i))
                    #salida_sampled = user1.reverse_sampling(ruido[:,1],X[:,1])


                    #array_images[cont_aux_continuo,:784]=salida_sampled[:784]
                    #cont_aux_continuo=cont_aux_continuo+1
                    #cont_aux=1
                #else:
                #   cont_aux=cont_aux+1

                #ESTA ZONA ES PARA CAMBIAR EL LEARNING RATE SI NO CAMBIA LA VARIACION
                #almac_er[almac]=error_dis
                #almac=almac+1
                #print(almac)
                #if almac==10:
                    #if (abs(almac_er[0]-almac_er[9])/10)<tol_pass:
                        #learning_rate=learning_rate/2
                        #learning_rate=learning_rate*(10**np.cos(((np.pi)/2)*cambio)) #va cambiando el learning rate oscilando entre 0 /10 o *10
                        #cambio= cambio+1

                        #print(learning_rate)

                    #almac=0

                print('el bueno',sum(l))
                salida_ploteable[m,cont]=sum(l) #i corresponde con T
                salida_ploteable_test[m,cont]=sum(l_test) #i corresponde con T
                cont=cont+1

                #print('aqui estoy')
                if abs(loss)<0.00000006:
                    errores=0
                epoch=epoch+1


                
            model_dict[i]=model
            print(int(i))
            print('while: ',enumerador)
            print(torch.cuda.memory_summary())
            enumerador=enumerador+1

    fnames = []
    fn = 'spir'
            
    plt.figure(dpi=100)
    for i in range(3):
        plt.plot(salida_ploteable[i,:].detach().cpu().numpy())
        plt.plot(salida_ploteable_test[i,:].detach().cpu().numpy(),'--')
    plt.ylabel('loss de todas las sample/batch')
    plt.xlabel('epochs')
    plt.xscale('log')
    plt.axis([0,700,0.1,1.1])
    plt.show()
    #print(l)
    fname = fn+str(t)+'.png'
    plt.savefig(fname)








from datetime import date
from datetime import datetime

#Día actual
today = date.today()

#Fecha actual
now = datetime.now()

print(today)
print(now)
#print(W)
today.strftime('%m/%d/%Y')
now.strftime('%m_%d_%Y_%H_%M_%S')
print(now)
nombre='pesos_batch'+'_'+now.strftime('%m_%d_%Y_%H_%M_%S')
#torch.save(model_dict,nombre) #lo pongo al fondo mejor por si falla

#from google.colab import drive
#drive.mount('/content/drive')
#torch.save(the_model.state_dict(), PATH)
"""SAMPLING"""
torch.save(model_dict.cpu(),nombre) #para salvar el modelo
#prediccion un vector de 700
#W = torch.load('./pesos_batch_12_23_2023_23_08_55') #aquí se puede cargar la matriz de pesos de una compilación hasta un error de 148
#print(W)

#prediccion un vector de 700
#W = torch.load('./pesos_buenos_100_samples_100_pasos_de_difusion') #aquí se puede cargar la matriz de pesos de una compilación hasta un error de 148
#print(W)
samplenum=1
user1=Difusion(torch.clone(data_bien),None,T)


salida_sampled = user1.reverse_sampling(None,X[T-1,samplenum,:].to(DEVICE),model_dict.to(DEVICE))
#salida_sampled = user1.reverse_sampling(ruido[:,1],X[:,1])

import matplotlib.pyplot as plt
plt.imshow(np.transpose(salida_sampled[:784].cpu().reshape(28,28)))

plt.figure(dpi=100)
plt.hist(salida_sampled[:784].cpu().numpy(),bins=40)

#print(torch.sum(abs(salida_sampled.cpu()-data_bien[:,samplenum])))#debería ser menos (pero es más)
#print(torch.sum(abs(X[T-1,samplenum,:]-data_bien[:,samplenum])))

"""Quizá lo que falla es la dependencia a cada tiempo ya que en el sampling estamos sacando una predicción del modelo para cada iteración de T. Entonces tendríamos que poner otra dimensión de pesoso para cada T y tambien iterar el entrenamiento para cada T, es decir una sigmoid para cada T al igual que hay ahora una sigmoid para cada punto."""

plt.figure(dpi=100)
plt.imshow(np.transpose(salida_sampled[:784].cpu().reshape(28,28)))
plt.savefig('hist1')

print(array_images[0,:784])

plt.figure(dpi=100)
plt.hist(array_images[1,:784].cpu().numpy(),bins=40)
plt.savefig('hist2')

plt.figure(dpi=100)
plt.hist(data_bien[:784,1].cpu().numpy(),bins=40)
plt.savefig('hist3')

plt.figure(dpi=100)
plt.plot(data_bien[:784,:].cpu().mean(1))
plt.savefig('hist4')

fnames = []
fn = 'spir'
for t in range(array_images.size(dim=0)):
    plt.figure(dpi=100)
    plt.imshow(np.transpose(array_images[t,:784].cpu().reshape(28,28)))
    fname = fn+str(t)+'.png'
    plt.savefig(fname)



fnames = []
fn = 'spir'
for t in range(array_images.size(dim=0)):
    fname = fn+str(t)+'.png'
    fnames.append(fname)



import imageio
import os
with imageio.get_writer('FiffGIF.gif',mode='I') as writer:
    for fname in fnames:
        image = imageio.imread(fname)
        writer.append_data(image)