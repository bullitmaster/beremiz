/*
 * DEBUGGER code
 * 
 * On "publish", when buffer is free, debugger stores arbitrary variables 
 * content into, and mark this buffer as filled
 * 
 * 
 * Buffer content is read asynchronously, (from non real time part), 
 * and then buffer marked free again.
 *  
 * 
 * */
#include "iec_types_all.h"
#include "POUS.h"
/*for memcpy*/
#include <string.h>
#include <stdio.h>

#define BUFFER_SIZE %(buffer_size)d
#define MAX_SUBSCRIBTION %(subscription_table_count)d

/* Atomically accessed variable for buffer state */
#define BUFFER_FREE 0
#define BUFFER_BUSY 1
static long buffer_state = BUFFER_FREE;

/* The buffer itself */
char debug_buffer[BUFFER_SIZE];

/* Buffer's cursor*/
static char* buffer_cursor = debug_buffer;

/***
 * Declare programs 
 **/
%(programs_declarations)s

/***
 * Declare global variables from resources and conf 
 **/
%(extern_variables_declarations)s

typedef void(*__for_each_variable_do_fp)(void*, __IEC_types_enum);
void __for_each_variable_do(__for_each_variable_do_fp fp)
{
%(for_each_variable_do_code)s
}

__IEC_types_enum __find_variable(unsigned int varindex, void ** varp)
{
    switch(varindex){
%(find_variable_case_code)s
     default:
      *varp = NULL;
      return UNKNOWN_ENUM;
    }
}

void __init_debug(void)
{
    buffer_state = BUFFER_FREE;
}

void __cleanup_debug(void)
{
}

void __retrieve_debug(void)
{
}

extern int TryEnterDebugSection(void);
extern void LeaveDebugSection(void);
extern long AtomicCompareExchange(long*, long, long);
extern void InitiateDebugTransfer(void);

extern unsigned long __tick;

#define __BufferDebugDataIterator_case_t(TYPENAME) \
        case TYPENAME##_ENUM :\
            flags = ((__IEC_##TYPENAME##_t *)varp)->flags;\
            ptrvalue = &((__IEC_##TYPENAME##_t *)varp)->value;\
            break;

#define __BufferDebugDataIterator_case_p(TYPENAME)\
        case TYPENAME##_P_ENUM :\
            flags = ((__IEC_##TYPENAME##_p *)varp)->flags;\
            ptrvalue = ((__IEC_##TYPENAME##_p *)varp)->value;\
            break;

void BufferDebugDataIterator(void* varp, __IEC_types_enum vartype)
{
    void *ptrvalue = NULL;
    char flags = 0;
    /* find data to copy*/
    switch(vartype){
        ANY(__BufferDebugDataIterator_case_t)
        ANY(__BufferDebugDataIterator_case_p)
    default:
        break;
    }
    if(flags && __IEC_DEBUG_FLAG){
        USINT size = __get_type_enum_size(vartype);
        /* compute next cursor positon*/
        char* next_cursor = buffer_cursor + size;
        /* if buffer not full */
        if(next_cursor <= debug_buffer + BUFFER_SIZE)
        {
            /* copy data to the buffer */
            memcpy(buffer_cursor, ptrvalue, size);
            /* increment cursor according size*/
            buffer_cursor = next_cursor;
        }else{
            /*TODO : signal overflow*/
        }
    }
}


void __publish_debug(void)
{
    /* Check there is no running debugger re-configuration */
    if(TryEnterDebugSection()){
        /* Lock buffer */
        long latest_state = AtomicCompareExchange(
            &buffer_state,
            BUFFER_FREE,
            BUFFER_BUSY);
            
        /* If buffer was free */
        if(latest_state == BUFFER_FREE)
        {
            /* Reset buffer cursor */
            buffer_cursor = debug_buffer;
            /* Iterate over all variables to fill debug buffer */
            __for_each_variable_do(BufferDebugDataIterator);
            
            /* Leave debug section,
             * Trigger asynchronous transmission 
             * (returns immediately) */
            InitiateDebugTransfer(); /* size */
        }
        LeaveDebugSection();
    }
}

#define __RegisterDebugVariable_case_t(TYPENAME) \
        case TYPENAME##_ENUM :\
            ((__IEC_##TYPENAME##_t *)varp)->flags |= flags;\
            if(force)\
             ((__IEC_##TYPENAME##_t *)varp)->value = *((TYPENAME *)force);\
            break;
#define __RegisterDebugVariable_case_p(TYPENAME)\
        case TYPENAME##_P_ENUM :\
            ((__IEC_##TYPENAME##_p *)varp)->flags |= flags;\
            if(force)\
             ((__IEC_##TYPENAME##_p *)varp)->fvalue = *((TYPENAME *)force);\
            break;
void RegisterDebugVariable(int idx, void* force)
{
    void *varp = NULL;
    unsigned char flags = force ? __IEC_DEBUG_FLAG | __IEC_FORCE_FLAG : __IEC_DEBUG_FLAG;
    switch(__find_variable(idx, &varp)){
        ANY(__RegisterDebugVariable_case_t)
        ANY(__RegisterDebugVariable_case_p)
    default:
        break;
    }
}

#define __ResetDebugVariablesIterator_case_t(TYPENAME) \
        case TYPENAME##_ENUM :\
            ((__IEC_##TYPENAME##_t *)varp)->flags &= ~(__IEC_DEBUG_FLAG|__IEC_FORCE_FLAG);\
            break;

#define __ResetDebugVariablesIterator_case_p(TYPENAME)\
        case TYPENAME##_P_ENUM :\
            ((__IEC_##TYPENAME##_p *)varp)->flags &= ~(__IEC_DEBUG_FLAG|__IEC_FORCE_FLAG);\
            break;

void ResetDebugVariablesIterator(void* varp, __IEC_types_enum vartype)
{
    /* force debug flag to 0*/
    switch(vartype){
        ANY(__ResetDebugVariablesIterator_case_t)
        ANY(__ResetDebugVariablesIterator_case_p)
    default:
        break;
    }
}

void ResetDebugVariables(void)
{
    __for_each_variable_do(ResetDebugVariablesIterator);
}

void FreeDebugData(void)
{
    /* atomically mark buffer as free */
    long latest_state;
    latest_state = AtomicCompareExchange(
        &buffer_state,
        BUFFER_BUSY,
        BUFFER_FREE);
}
int WaitDebugData(unsigned long *tick);
/* Wait until debug data ready and return pointer to it */
int GetDebugData(unsigned long *tick, unsigned long *size, void **buffer){
    int res = WaitDebugData(tick);
    *size = buffer_cursor - debug_buffer;
    *buffer = debug_buffer;
    return res;
}

